"""Main application entry point for the RAG demo.

This file wires together three pieces:

1. FastAPI, which runs the web server.
2. Inngest, which lets us define event-driven background functions.
3. The RAG helpers, which chunk PDFs, create embeddings, store vectors,
   and answer questions from the stored content.

The important beginner-friendly idea is this:

- Starting the app does not immediately process a PDF or answer a question.
- Instead, the app registers functions that wait for specific events.
- When an event arrives, Inngest runs the matching function.
"""

import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import RAGQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc

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
    trigger=inngest.TriggerEvent(event="rag/inngest.pdf")
)

async def rag_inngest_pdf(ctx: inngest.Context):
    """Ingest a PDF into the vector database when a PDF event is received.

    Expected event data:
    - `pdf_path`: local path to the PDF file
    - `source_id` (optional): a readable identifier for the document

    High-level workflow:
    1. Read the PDF and split it into smaller text chunks.
    2. Convert each chunk into an embedding vector.
    3. Store those vectors in Qdrant so they can be searched later.
    """

    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:
        """Load the PDF from disk and break it into text chunks."""
        pdf_path = ctx.event.data["pdf_path"]
        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        """Embed the chunks and save them into Qdrant.

        Each chunk gets:
        - a stable ID, so the same document can be reprocessed consistently
        - a vector embedding, which is what semantic search uses
        - payload metadata, so we can recover the original text and source later
        """
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    # `ctx.step.run(...)` tells Inngest to treat each block as a named step.
    # That makes the function easier to inspect and retry in the Inngest UI.
    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)

async def rag_query_pdf_ai(ctx: inngest.Context):
    """Answer a user's question using text previously stored from PDFs.

    Expected event data:
    - `question`: the user's question
    - `top_k` (optional): how many relevant chunks to retrieve from Qdrant

    High-level workflow:
    1. Embed the question into a vector.
    2. Search Qdrant for the most similar PDF chunks.
    3. Send those chunks to the LLM as context.
    4. Return the answer plus the sources used.
    """

    def _search(question: str, top_k: int = 5) -> RAGSearchResult:
        """Find the most relevant stored chunks for the user's question."""
        query_vec = embed_texts([question])[0]
        store = QdrantStorage()
        found = store.search(query_vec, top_k)
        return RAGSearchResult(contexts=found["contexts"], sources=found["sources"])

    question = ctx.event.data["question"]
    top_k = int(ctx.event.data.get("top_k", 5))

    found = await ctx.step.run("embed-and-search", lambda: _search(question, top_k), output_type=RAGSearchResult)

    # Join the retrieved chunks into one block of text that the model can read.
    context_block = "\n\n".join(f"- {c}" for c in found.contexts)
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
    return {"answer": answer, "sources": found.sources, "num_contexts": len(found.contexts)}

# FastAPI hosts the HTTP endpoint that Inngest talks to.
app = FastAPI()

# Register the Inngest functions on the FastAPI app.
# After this, the app can receive Inngest requests at the mounted route.
inngest.fast_api.serve(app, inngest_client, [rag_inngest_pdf, rag_query_pdf_ai])
