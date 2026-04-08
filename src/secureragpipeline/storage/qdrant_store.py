"""Small wrapper around Qdrant for storing and searching embeddings."""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from ..config import DEFAULT_EMBED_DIM, DEFAULT_QDRANT_COLLECTION, DEFAULT_QDRANT_URL
from ..models.payloads import RetrievedChunk


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

    def list_documents(self, limit: int = 200):
        """Return simple per-document summaries from stored payload metadata."""
        points, _next_page = self.client.scroll(
            collection_name=self.collection,
            with_payload=True,
            limit=limit,
        )

        summaries: dict[str, dict] = {}
        for point in points:
            payload = getattr(point, "payload", None) or {}
            doc_id = payload.get("doc_id") or payload.get("source") or str(getattr(point, "id", "unknown"))
            summary = summaries.setdefault(
                doc_id,
                {
                    "doc_id": doc_id,
                    "source": payload.get("source", ""),
                    "classification": payload.get("classification", "internal"),
                    "trust_level": payload.get("trust_level", "user_uploaded"),
                    "ingest_decision": payload.get("ingest_decision", "allow"),
                    "ingest_scan_flags": list(payload.get("ingest_scan_flags", [])),
                    "created_at": payload.get("created_at", ""),
                    "chunk_count": 0,
                },
            )
            summary["chunk_count"] += 1

        return sorted(summaries.values(), key=lambda item: item.get("created_at", ""), reverse=True)

    def delete_document(self, doc_id: str) -> None:
        """Delete all stored chunks belonging to one document ID."""
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
        )
