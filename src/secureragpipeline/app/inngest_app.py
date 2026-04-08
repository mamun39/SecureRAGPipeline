"""FastAPI and Inngest application entrypoint."""

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
import inngest
import inngest.fast_api

from ..workflows.ingest_pdf import run_ingest_pdf
from ..workflows.query_pdf import run_query_pdf


load_dotenv()

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)


@inngest_client.create_function(
    fn_id="RAG: Inngest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def rag_inngest_pdf(ctx: inngest.Context):
    """Ingest a PDF into the vector database when a PDF event is received."""
    return await run_ingest_pdf(ctx)


@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai"),
)
async def rag_query_pdf_ai(ctx: inngest.Context):
    """Answer a user's question using text previously stored from PDFs."""
    return await run_query_pdf(ctx)


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [rag_inngest_pdf, rag_query_pdf_ai])
