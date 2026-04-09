"""Workflow orchestration for PDF-backed question answering."""

import os
import re

import inngest
from inngest.experimental import ai
from openai import AsyncOpenAI

from ..config import (
    DEFAULT_ALLOW_LOW_TRUST,
    DEFAULT_DEMO_TENANT_ID,
    DEFAULT_DEMO_USER_ROLE,
    DEFAULT_EVAL_LLM_TEMPERATURE,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TEMPERATURE,
)
from ..ingestion.embeddings import embed_texts
from ..models.policy import RetrievalPolicyContext
from ..models.results import (
    ChunkTraceEntry,
    OutputFilterResult,
    QueryAPIResponse,
    QueryRetrievalTrace,
    RAGQueryResult,
    RAGSearchResult,
)
from ..security.audit import log_security_event
from ..security.output_filter import SAFE_REFUSAL_MESSAGE, screen_generated_answer
from ..security.retrieval_policy import (
    allowed_classifications_for_role,
    build_retrieval_filter,
)
from ..security.safe_context import build_safe_context
from ..storage.qdrant_store import QdrantStorage


DISALLOWED_REQUEST_PATTERNS = {
    "restricted": [
        re.compile(r"\bbreak-glass\b", re.IGNORECASE),
        re.compile(r"\badmin-only\b", re.IGNORECASE),
        re.compile(r"\brestricted\b.*\b(guidance|instructions?|details|information|content|material|access)\b", re.IGNORECASE),
    ],
    "confidential": [
        re.compile(r"\bconfidential\b.*\b(guidance|instructions?|details|information|content|material|planning)\b", re.IGNORECASE),
    ],
    "internal": [
        re.compile(r"\binternal-only\b", re.IGNORECASE),
        re.compile(r"\bemployee-only\b", re.IGNORECASE),
    ],
}


def _search(
    question: str,
    *,
    top_k: int = 5,
    user_role: str = DEFAULT_DEMO_USER_ROLE,
    tenant_id: str = DEFAULT_DEMO_TENANT_ID,
    source_id: str | None = None,
) -> RAGSearchResult:
    query_vec = embed_texts([question])[0]
    store = QdrantStorage()
    policy_context = RetrievalPolicyContext(
        tenant_id=tenant_id,
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


def _build_query_messages(user_content: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "You answer question using only the provided context."},
        {"role": "user", "content": user_content},
    ]


def _build_infer_body(user_content: str, temperature: float) -> dict:
    return {
        "max_tokens": DEFAULT_LLM_MAX_TOKENS,
        "temperature": temperature,
        "messages": _build_query_messages(user_content),
    }


def _requested_disallowed_classification(question: str, allowed_classifications: list[str]) -> str | None:
    """Return an explicitly requested classification that the role cannot access."""
    for classification in ("restricted", "confidential", "internal"):
        if classification in allowed_classifications:
            continue
        if any(pattern.search(question) for pattern in DISALLOWED_REQUEST_PATTERNS[classification]):
            return classification
    return None


async def execute_query(
    *,
    question: str,
    top_k: int = 5,
    user_role: str = DEFAULT_DEMO_USER_ROLE,
    tenant_id: str = DEFAULT_DEMO_TENANT_ID,
    source_id: str | None = None,
    generate_answer,
    temperature: float = DEFAULT_LLM_TEMPERATURE,
) -> RAGQueryResult:
    """Run the shared query pipeline and return the structured result."""
    allowed_classifications = allowed_classifications_for_role(user_role)
    found = _search(
        question,
        top_k=top_k,
        user_role=user_role,
        tenant_id=tenant_id,
        source_id=source_id,
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
    requested_disallowed_classification = _requested_disallowed_classification(question, allowed_classifications)
    if requested_disallowed_classification:
        output_filter_result = OutputFilterResult(
            decision="redact",
            filtered_text=SAFE_REFUSAL_MESSAGE,
            reasons=["requested_classification_not_allowed"],
        )
        answer = output_filter_result.filtered_text
    else:
        res = await generate_answer(_build_infer_body(user_content, temperature))
        answer = res["choices"][0]["message"]["content"].strip()
        output_filter_result = screen_generated_answer(
            answer,
            question=question,
            num_contexts=len(safe_chunks),
        )
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
    return result


async def run_api_query(
    *,
    question: str,
    top_k: int = 5,
    user_role: str = DEFAULT_DEMO_USER_ROLE,
    tenant_id: str = DEFAULT_DEMO_TENANT_ID,
    source_id: str | None = None,
    temperature: float = DEFAULT_EVAL_LLM_TEMPERATURE,
) -> QueryAPIResponse:
    """Run the query pipeline for the external API response contract."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_answer(body: dict) -> dict:
        response = await client.chat.completions.create(
            model=DEFAULT_LLM_MODEL,
            max_tokens=body["max_tokens"],
            temperature=body["temperature"],
            messages=body["messages"],
        )
        return response.model_dump()

    result = await execute_query(
        question=question,
        top_k=top_k,
        user_role=user_role,
        tenant_id=tenant_id,
        source_id=source_id,
        generate_answer=generate_answer,
        temperature=temperature,
    )
    return QueryAPIResponse(
        answer=result.answer,
        answer_decision=result.output_filter_decision,
        role=user_role,
        tenant_id=tenant_id,
        retrieved_count=len(result.retrieved_chunks),
        excluded_count=len(result.excluded_chunks),
        retrieval_trace=QueryRetrievalTrace(
            retrieved=result.retrieved_chunks,
            safe=result.safe_chunks,
            excluded=result.excluded_chunks,
        ),
        output_filter_reasons=result.output_filter_reasons,
    )


async def run_query_pdf(ctx: inngest.Context) -> dict:
    """Execute the query workflow and return the serialized result."""
    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))
    source_id = ctx.event.data.get("source_id")
    effective_role = ctx.event.data.get("user_role", DEFAULT_DEMO_USER_ROLE)
    effective_tenant = ctx.event.data.get("tenant_id", DEFAULT_DEMO_TENANT_ID)

    async def generate_answer(body: dict) -> dict:
        adapter = ai.openai.Adapter(
            auth_key=os.getenv("OPENAI_API_KEY"),
            model=DEFAULT_LLM_MODEL,
        )
        return await ctx.step.ai.infer("llm-answer", adapter=adapter, body=body)

    result = await execute_query(
        question=question,
        top_k=top_k,
        user_role=effective_role,
        tenant_id=effective_tenant,
        source_id=source_id,
        generate_answer=generate_answer,
        temperature=DEFAULT_LLM_TEMPERATURE,
    )
    return result.model_dump()
