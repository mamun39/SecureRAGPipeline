"""Small wrapper around Qdrant for storing and searching embeddings.

This module hides the low-level Qdrant client calls behind a simple class.
For this project, Qdrant is used as the vector database for RAG:

- `upsert(...)` stores text chunk embeddings.
- `search(...)` finds the chunks most similar to a question embedding.

If you are new to vector databases, think of Qdrant as a database that is
good at answering: "Which stored vectors are closest to this new vector?"
"""

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct


class QdrantStorage:
    """Convenience wrapper for one Qdrant collection.

    A collection in Qdrant is similar to a table in a relational database.
    In this project, the collection stores:
    - an ID for each text chunk
    - the chunk's embedding vector
    - payload metadata such as the original text and source document
    """

    def __init__(self, url="http://localhost:6333", collection="docs", dim=3072):
        """Connect to Qdrant and create the collection if it does not exist.

        Args:
            url: Address of the Qdrant server.
            collection: Name of the collection to use.
            dim: Size of each embedding vector.

        The `dim` value must match the size produced by your embedding model.
        """
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids, vectors, payloads):
        """Insert or update a batch of vectors in Qdrant.

        Args:
            ids: Unique IDs for the stored chunks.
            vectors: Embedding vectors for those chunks.
            payloads: Extra metadata stored with each vector.

        "Upsert" means:
        - insert if the point does not exist yet
        - update/replace it if it already exists
        """
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vector, top_k: int = 5):
        """Search for the most relevant stored chunks for a query vector.

        Args:
            query_vector: The embedding of the user's question.
            top_k: Maximum number of nearest matches to return.

        Returns:
            A dictionary containing:
            - `contexts`: the matching chunk texts
            - `sources`: the unique source identifiers for those chunks
        """
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_k,
        )

        # In this qdrant-client version, nearest-neighbor results live inside
        # `response.points` rather than being returned directly as a list.
        results = response.points

        contexts = []
        sources = set()

        for r in results:
            # The payload is the metadata we stored during `upsert(...)`.
            payload = getattr(r, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                contexts.append(text)
            if source:
                sources.add(source)

        return {"contexts": contexts, "sources": list(sources)}








