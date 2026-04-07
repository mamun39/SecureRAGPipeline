"""Workflow result models."""

import pydantic

from .payloads import RetrievedChunk


class IngestScanResult(pydantic.BaseModel):
    """Result of a basic ingestion-time security scan."""

    score: int = 0
    flags: list[str] = pydantic.Field(default_factory=list)
    decision: str = "allow"


class OutputFilterResult(pydantic.BaseModel):
    """Result of screening a generated answer before returning it."""

    decision: str = "allow"
    filtered_text: str
    reasons: list[str] = pydantic.Field(default_factory=list)


class RAGChunkAndSrc(pydantic.BaseModel):
    """Represents text chunks extracted from one source document."""

    chunks: list[str]
    source_id: str = None


class RAGUpsertResult(pydantic.BaseModel):
    """Represents the result of storing chunk embeddings in the vector database."""

    ingested: int
    classification: str = "internal"
    trust_level: str = "user_uploaded"
    scan_decision: str = "allow"
    scan_flags: list[str] = pydantic.Field(default_factory=list)
    message: str | None = None


class RAGSearchResult(pydantic.BaseModel):
    """Represents retrieval results from the vector database."""

    contexts: list[str]
    sources: list[str]
    chunks: list[RetrievedChunk] = pydantic.Field(default_factory=list)


class ChunkTraceEntry(pydantic.BaseModel):
    """Trace-friendly representation of a retrieved chunk and its handling."""

    source: str = ""
    classification: str = "internal"
    trust_level: str = "user_uploaded"
    ingest_decision: str = "allow"
    ingest_scan_flags: list[str] = pydantic.Field(default_factory=list)
    text_preview: str = ""
    exclusion_reason: str | None = None


class RAGQueryResult(pydantic.BaseModel):
    """Represents the final RAG answer returned to the caller."""

    answer: str
    sources: list[str]
    num_contexts: int
    user_role: str
    allowed_classifications: list[str] = pydantic.Field(default_factory=list)
    output_filter_decision: str = "allow"
    output_filter_reasons: list[str] = pydantic.Field(default_factory=list)
    retrieved_chunks: list[ChunkTraceEntry] = pydantic.Field(default_factory=list)
    safe_chunks: list[ChunkTraceEntry] = pydantic.Field(default_factory=list)
    excluded_chunks: list[ChunkTraceEntry] = pydantic.Field(default_factory=list)
