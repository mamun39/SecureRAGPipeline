"""Utilities for loading PDF text and turning it into embeddings."""

from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

from ragagent.config import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBED_DIM,
    DEFAULT_EMBED_MODEL,
)


load_dotenv()

client = OpenAI()

EMBED_MODEL = DEFAULT_EMBED_MODEL
EMBED_DIM = DEFAULT_EMBED_DIM

splitter = SentenceSplitter(chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP)


def load_and_chunk_pdf(path: str):
    """Read a PDF file and split its text into smaller chunks."""
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for text in texts:
        chunks.extend(splitter.split_text(text))
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert text strings into embedding vectors using OpenAI."""
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
