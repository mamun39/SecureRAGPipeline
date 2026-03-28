"""Utilities for loading PDF text and turning it into embeddings.

This module handles the "prepare the data" part of the RAG pipeline:

1. Read text from a PDF file.
2. Split that text into smaller chunks.
3. Convert each chunk into an embedding vector using OpenAI.

These chunks and vectors are then stored in Qdrant so they can be searched
later when a user asks a question.
"""

from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

# Load environment variables before creating the OpenAI client.
load_dotenv()

# The OpenAI client reads the API key from environment variables.
client = OpenAI()

# This model returns 3072-dimensional embedding vectors.
EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072

# SentenceSplitter breaks long text into overlapping chunks.
# Overlap helps preserve context between neighboring chunks.
splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    """Read a PDF file and split its text into smaller chunks.

    Args:
        path: Path to the PDF file on disk.

    Returns:
        A list of text chunks.

    Why chunking is needed:
    - Long documents are harder to search and send to an LLM all at once.
    - Smaller chunks make retrieval more precise.
    """
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert text strings into embedding vectors using OpenAI.

    Args:
        texts: A list of strings to embed.

    Returns:
        A list of vectors, one vector per input string.

    An embedding is a list of numbers that captures semantic meaning.
    Similar text usually produces similar vectors.
    """
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]
