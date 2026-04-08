"""Workflow orchestration for PDF-backed question answering."""

import os

import inngest
from inngest.experimental import ai

from ..config import (
    DEFAULT_ALLOW_LOW_TRUST,
    DEFAULT_DEMO_TENANT_ID,
    DEFAULT_DEMO_USER_ROLE,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TEMPERATURE,
)
from ..ingestion.embeddings import embed_texts
from ..models.policy import RetrievalPolicyContext
from ..models.results import ChunkTraceEntry, RAGQueryResult, RAGSearchResult
from ..security.audit import log_security_event
from ..security.output_filter import screen_generated_answer
from ..security.retrieval_policy import (
    allowed_classifications_for_role,
    build_retrieval_filter,
)
from ..security.safe_context import build_safe_context
from ..storage.qdrant_store import QdrantStorage


async def run_query_pdf(ctx: inngest.Context) -> dict:
    """Execute the query workflow and return the serialized result."""

    def _search(question: str, top_k: int = 5, source_id: str | None = None) -> RAGSearchResult:
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        user_role = ctx.event.data.get("user_role", DEFAULT_DEMO_USER_ROLE)
        policy_context = RetrievalPolicyContext(
            tenant_id=DEFAULT_DEMO_TENANT_ID,
            # Real auth should populate user_role and tenant context here.
            user_role=user_role,
            allowed_classifications=allowed_classifications_for_role(user_role),
            allow_low_trust=DEFAULT_ALLOW_LOW_TRUST,
        )
        query_filter = build_retrieval_filter(policy_context, source_id=source_id)
        log_security_event(
            "retrieval_policy_context_used",
            tenant_id=policy_context.tenant_id,
            user_role=policy_context.user_role,
            allowed_classifications=policy_context.allowed_classifications,
            allow_low_trust=policy_context.allow_low_trust,
            source_id=source_id,
        )
        found = store.search(query_vec, top_k, query_filter=query_filter)
        log_security_event(
            "retrieved_chunk_identifiers",
            source_id=source_id,
            chunk_count=len(found["chunks"]),
            chunks=[
                {
                    "source": chunk.source,
                    "classification": chunk.classification,
                    "trust_level": chunk.trust_level,
                }
                for chunk in found["chunks"]
            ],
        )
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"], chunks=found["chunks"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))
    source_id = ctx.event.data.get("source_id")
    user_role = ctx.event.data.get("user_role", DEFAULT_DEMO_USER_ROLE)
    allowed_classifications = allowed_classifications_for_role(user_role)

    found = await ctx.step.run(
        "embed-and-search",
        lambda: _search(question, top_k, source_id=source_id),
        output_type=RAGSearchResult,
    )

    context_block, safe_chunks, safe_trace, excluded_trace = build_safe_context(found.chunks)
    retrieved_trace = [
        ChunkTraceEntry(
            source=chunk.source,
            classification=chunk.classification,
            trust_level=chunk.trust_level,
            ingest_decision=chunk.ingest_decision,
            ingest_scan_flags=chunk.ingest_scan_flags,
            text_preview=chunk.text[:160],
        )
        for chunk in found.chunks
    ]
    user_content = (
        "Use the following context to answer the question. \n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above"
    )

    adapter = ai.openai.Adapter(
        auth_key=os.getenv("OPENAI_API_KEY"),
        model=DEFAULT_LLM_MODEL,
    )

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": DEFAULT_LLM_MAX_TOKENS,
            "temperature": DEFAULT_LLM_TEMPERATURE,
            "messages": [
                {"role": "system", "content": "You answer question using only the provided context."},
                {"role": "user", "content": user_content},
            ],
        },
    )

    answer = res["choices"][0]["message"]["content"].strip()
    output_filter_result = screen_generated_answer(answer)
    log_security_event(
        "output_filter_decision",
        decision=output_filter_result.decision,
        reasons=output_filter_result.reasons,
        answer_length=len(answer),
    )
    result = RAGQueryResult(
        answer=output_filter_result.filtered_text,
        sources=found.sources,
        num_contexts=len(safe_chunks),
        user_role=user_role,
        allowed_classifications=allowed_classifications,
        output_filter_decision=output_filter_result.decision,
        output_filter_reasons=output_filter_result.reasons,
        retrieved_chunks=retrieved_trace,
        safe_chunks=safe_trace,
        excluded_chunks=excluded_trace,
    )
    return result.model_dump()
