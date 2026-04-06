"""Embedding generation helpers."""

from dotenv import load_dotenv
from openai import OpenAI

from ragagent.config import DEFAULT_EMBED_DIM, DEFAULT_EMBED_MODEL


load_dotenv()

client = OpenAI()

EMBED_MODEL = DEFAULT_EMBED_MODEL
EMBED_DIM = DEFAULT_EMBED_DIM


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert text strings into embedding vectors using OpenAI."""
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
