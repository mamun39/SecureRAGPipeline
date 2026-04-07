"""Workflow orchestration for PDF ingestion."""

import datetime
import hashlib
import logging
import uuid

import inngest

from ..ingestion.embeddings import embed_texts
from ..ingestion.loader import load_and_chunk_pdf
from ..models.payloads import RAGChunkPayload
from ..models.results import RAGChunkAndSrc, RAGUpsertResult
from ..security.audit import log_security_event
from ..security.ingestion_scanner import scan_document_text
from ..storage.qdrant_store import QdrantStorage


async def run_ingest_pdf(ctx: inngest.Context) -> dict:
    """Execute the PDF ingestion workflow and return the serialized result."""

    def _load(context: inngest.Context) -> RAGChunkAndSrc:
        pdf_path = context.event.data["pdf_path"]
        source_id = context.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        classification = ctx.event.data.get("classification", "internal")
        trust_level = ctx.event.data.get("trust_level", "user_uploaded")
        created_at = datetime.datetime.now(datetime.UTC).isoformat()
        scan_result = scan_document_text("\n".join(chunks))
        log_security_event(
            "ingestion_scan_result",
            source_id=source_id,
            score=scan_result.score,
            flags=scan_result.flags,
            decision=scan_result.decision,
            chunk_count=len(chunks),
        )
        if scan_result.decision == "quarantine":
            message = (
                f"Quarantined document '{source_id}' during ingestion due to "
                f"scan flags: {', '.join(scan_result.flags) or 'none'}"
            )
            log_security_event(
                "quarantine_decision",
                source_id=source_id,
                flags=scan_result.flags,
                reason=message,
            )
            logging.getLogger("uvicorn").warning(message)
            return RAGUpsertResult(
                ingested=0,
                classification=classification,
                trust_level=trust_level,
                scan_decision=scan_result.decision,
                scan_flags=scan_result.flags,
                message=message,
            )

        if scan_result.decision == "review":
            logging.getLogger("uvicorn").info(
                "Ingesting review-marked document '%s' with scan flags: %s",
                source_id,
                ", ".join(scan_result.flags) or "none",
            )

        vecs = embed_texts(chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [
            RAGChunkPayload(
                doc_id=source_id,
                chunk_id=ids[i],
                source=source_id,
                text=chunks[i],
                classification=classification,
                trust_level=trust_level,
                ingest_scan_flags=scan_result.flags,
                ingest_decision=scan_result.decision,
                content_hash=hashlib.sha256(chunks[i].encode("utf-8")).hexdigest(),
                created_at=created_at,
            ).model_dump()
            for i in range(len(chunks))
        ]
        QdrantStorage().upsert(ids, vecs, payloads)
        return RAGUpsertResult(
            ingested=len(chunks),
            classification=classification,
            trust_level=trust_level,
            scan_decision=scan_result.decision,
            scan_flags=scan_result.flags,
            message=f"Ingested document '{source_id}' with decision '{scan_result.decision}'.",
        )

    chunks_and_src = await ctx.step.run("load-and-chunk", lambda: _load(ctx), output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run("embed-and-upsert", lambda: _upsert(chunks_and_src), output_type=RAGUpsertResult)
    return ingested.model_dump()
