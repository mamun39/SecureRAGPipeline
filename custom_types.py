"""Pydantic models used to pass structured data through the RAG workflow.

These models make the code easier to read and safer to use because each step
can declare exactly what shape of data it expects and returns.
"""

import pydantic


class ChunkSecurityMetadata(pydantic.BaseModel):
    """Security-related metadata stored with each chunk payload.

    These fields are intentionally simple defaults for the demo app so later
    phases can add scanning, authorization, and safety logic without needing
    to redesign the stored payload shape.
    """

    doc_id: str
    chunk_id: str
    tenant_id: str = "demo"
    owner_id: str = "local_user"
    classification: str = "internal"
    trust_level: str = "user_uploaded"
    ingest_scan_flags: list[str] = pydantic.Field(default_factory=list)
    ingest_decision: str = "allow"
    content_hash: str
    created_at: str


class RAGChunkPayload(ChunkSecurityMetadata):
    """Full payload stored in Qdrant for one chunk."""

    source: str
    text: str


class IngestScanResult(pydantic.BaseModel):
    """Result of a basic ingestion-time security scan."""

    score: int = 0
    flags: list[str] = pydantic.Field(default_factory=list)
    decision: str = "allow"


class RAGChunkAndSrc(pydantic.BaseModel):
    """Represents text chunks extracted from one source document.

    Attributes:
        chunks: The list of text chunks created from the document.
        source_id: Identifier for the original source, such as a file path.
    """

    chunks: list[str]
    source_id: str = None


class RAGUpsertResult(pydantic.BaseModel):
    """Represents the result of storing chunk embeddings in the vector database.

    Attributes:
        ingested: Number of chunks successfully prepared and stored.
        scan_decision: Final ingestion scan decision for the document.
        scan_flags: Suspicious phrases detected during ingestion scanning.
        message: Human-readable ingestion status.
    """

    ingested: int
    scan_decision: str = "allow"
    scan_flags: list[str] = pydantic.Field(default_factory=list)
    message: str | None = None


class RAGSearchResult(pydantic.BaseModel):
    """Represents retrieval results from the vector database.

    Attributes:
        contexts: The retrieved text chunks relevant to the user's question.
        sources: The unique source identifiers for those chunks.
    """

    contexts: list[str]
    sources: list[str]


class RAGQueryResult(pydantic.BaseModel):
    """Represents the final RAG answer returned to the caller.

    Attributes:
        answer: The LLM-generated answer.
        sources: The sources used to build that answer.
        num_contexts: Number of retrieved chunks supplied to the model.
    """

    answer: str
    sources: list[str]
    num_contexts: int
