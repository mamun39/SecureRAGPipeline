"""Small wrapper around Qdrant for storing and searching embeddings."""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
)

from ragagent.models.payloads import RetrievedChunk
from ragagent.config import DEFAULT_EMBED_DIM, DEFAULT_QDRANT_COLLECTION, DEFAULT_QDRANT_URL


class QdrantStorage:
    """Convenience wrapper for one Qdrant collection."""

    def __init__(
        self,
        url: str = DEFAULT_QDRANT_URL,
        collection: str = DEFAULT_QDRANT_COLLECTION,
        dim: int = DEFAULT_EMBED_DIM,
    ):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def upsert(self, ids, vectors, payloads):
        """Insert or update a batch of vectors in Qdrant."""
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        query_vector,
        top_k: int = 5,
        query_filter: Filter | None = None,
    ):
        """Search for the most relevant stored chunks for a query vector."""
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_k,
            query_filter=query_filter,
        )

        results = response.points

        contexts = []
        sources = set()
        chunks = []

        for result in results:
            payload = getattr(result, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            classification = payload.get("classification", "internal")
            trust_level = payload.get("trust_level", "user_uploaded")
            ingest_decision = payload.get("ingest_decision", "allow")
            ingest_scan_flags = payload.get("ingest_scan_flags", [])
            if text:
                contexts.append(text)
                chunks.append(
                    RetrievedChunk(
                        text=text,
                        source=source,
                        classification=classification,
                        trust_level=trust_level,
                        ingest_decision=ingest_decision,
                        ingest_scan_flags=ingest_scan_flags,
                    )
                )
            if source:
                sources.add(source)

        return {"contexts": contexts, "sources": list(sources), "chunks": chunks}
