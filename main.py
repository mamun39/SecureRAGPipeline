"""Main application entry point for the RAG demo."""

import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import os
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import (
    RAGQueryResult,
    RAGSearchResult,
    RAGUpsertResult,
    RAGChunkAndSrc,
    RAGChunkPayload,
    RetrievalPolicyContext,
)
from security_ingestion import scan_document_text
from security_retrieval_policy import allowed_classifications_for_role
from security_safe_context import build_safe_context
from security_output_filter import screen_generated_answer
from security_audit import log_security_event
from ragagent.workflows.ingest_pdf import run_ingest_pdf

# Load values from the local .env file before the app starts.
# This is where API keys and other local configuration usually live.
load_dotenv()

# Create one shared Inngest client for this application.
# Inngest uses this object to register and serve event-driven functions.
inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id="RAG: Inngest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf")
)

async def rag_inngest_pdf(ctx: inngest.Context):
    """Ingest a PDF into the vector database when a PDF event is received."""
    return await run_ingest_pdf(ctx)

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)

async def rag_query_pdf_ai(ctx: inngest.Context):
    """Answer a user's question using text previously stored from PDFs.

    Expected event data:
    - `question`: the user's question
    - `top_k` (optional): how many relevant chunks to retrieve from Qdrant
    - `source_id` (optional): restrict retrieval to one ingested source

    High-level workflow:
    1. Embed the question into a vector.
    2. Search Qdrant for the most similar PDF chunks.
    3. Send those chunks to the LLM as context.
    4. Return the answer plus the sources used.
    """

    def _search(question: str, top_k: int = 5, source_id: str | None = None) -> RAGSearchResult:
        """Find the most relevant stored chunks for the user's question."""
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        user_role = ctx.event.data.get("user_role", "employee")
        policy_context = RetrievalPolicyContext(
            tenant_id="demo",
            # Real auth should populate user_role and tenant context here.
            user_role=user_role,
            allowed_classifications=allowed_classifications_for_role(user_role),
            allow_low_trust=False,
        )
        log_security_event(
            "retrieval_policy_context_used",
            tenant_id=policy_context.tenant_id,
            user_role=policy_context.user_role,
            allowed_classifications=policy_context.allowed_classifications,
            allow_low_trust=policy_context.allow_low_trust,
            source_id=source_id,
        )
        found = store.search(query_vec, top_k, source_id=source_id, policy_context=policy_context)
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

    found = await ctx.step.run(
        "embed-and-search",
        lambda: _search(question, top_k, source_id=source_id),
        output_type=RAGSearchResult,
    )

    context_block, safe_chunks = build_safe_context(found.chunks)
    user_content = (
        "Use the following context to answer the question. \n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n"
        "Answer concisely using the context above"
    )

    # The adapter tells Inngest which model provider to call and which model to use.
    adapter = ai.openai.Adapter(
        auth_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini"
    )

    # This is the actual LLM call. The model receives the retrieved context
    # and is instructed to answer only from that context.
    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 1024,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You answer question using only the provided context."},
                {"role": "user", "content": user_content}
            ]
        }
    )

    answer = res["choices"][0]["message"]["content"].strip()
    output_filter_result = screen_generated_answer(answer)
    log_security_event(
        "output_filter_decision",
        decision=output_filter_result.decision,
        reasons=output_filter_result.reasons,
        answer_length=len(answer),
    )
    if output_filter_result.decision != "allow":
        logging.getLogger("uvicorn").warning(
            "Output filter decision=%s reasons=%s",
            output_filter_result.decision,
            ",".join(output_filter_result.reasons) or "none",
        )
    return {
        "answer": output_filter_result.filtered_text,
        "sources": found.sources,
        "num_contexts": len(safe_chunks),
    }

# FastAPI hosts the HTTP endpoint that Inngest talks to.
app = FastAPI()

# Register the Inngest functions on the FastAPI app.
# After this, the app can receive Inngest requests at the mounted route.
inngest.fast_api.serve(app, inngest_client, [rag_inngest_pdf, rag_query_pdf_ai])
