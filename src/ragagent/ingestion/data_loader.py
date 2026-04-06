"""Compatibility re-exports for ingestion loading and embedding helpers."""

from ragagent.ingestion.embeddings import EMBED_DIM, EMBED_MODEL, embed_texts
from ragagent.ingestion.loader import load_and_chunk_pdf

__all__ = [
    "EMBED_DIM",
    "EMBED_MODEL",
    "embed_texts",
    "load_and_chunk_pdf",
]
