"""Pydantic models used to pass structured data through the RAG workflow.

These models make the code easier to read and safer to use because each step
can declare exactly what shape of data it expects and returns.
"""

import pydantic


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
    """

    ingested: int


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
