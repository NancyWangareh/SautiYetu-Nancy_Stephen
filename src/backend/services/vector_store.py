"""
Vector store — Qdrant (local file-based) for budget chunk storage.
Supports multiple documents via namespace filtering.
"""
import logging
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue

from ..config import config

logger = logging.getLogger(__name__)

COLLECTION_NAME = "budget_chunks"


class VectorStore:
    """Qdrant local vector store with multi-document support."""

    def __init__(self, path: str | Path | None = None):
        store_path = str(path or config.QDRANT_PATH)
        Path(store_path).mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=store_path)
        logger.info("Qdrant store at: %s", store_path)

    def collection_exists(self) -> bool:
        try:
            names = [c.name for c in self.client.get_collections().collections]
            return COLLECTION_NAME in names
        except Exception:
            return False

    def create_collection(self, vector_size: int, force: bool = False):
        if self.collection_exists():
            if force:
                logger.info("Recreating collection '%s'", COLLECTION_NAME)
                self.client.delete_collection(COLLECTION_NAME)
            else:
                logger.info("Collection '%s' already exists", COLLECTION_NAME)
                return

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created collection '%s' (dim=%d)", COLLECTION_NAME, vector_size)

    def upsert_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        document_id: str | None = None,
        batch_size: int = 100,
    ) -> int:
        """
        Upsert chunks with optional document namespace.

        document_id: tracks which budget PDF these chunks came from.
        """
        # Start IDs after existing points so we never collide
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            next_id = info.points_count
        except Exception:
            next_id = 0

        total = len(chunks)
        batch_points = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            batch_points.append(
                PointStruct(
                    id=next_id + i,
                    vector=embedding,
                    payload={
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "page_number": chunk["page_number"],
                        "document_id": document_id,
                        "metadata": chunk.get("metadata", {}),
                    },
                )
            )

            if len(batch_points) >= batch_size or i == total - 1:
                self.client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch_points,
                    wait=True,
                )
                logger.debug("Upserted %d points", len(batch_points))
                batch_points = []

        logger.info("Upserted %d chunks (doc=%s)", total, document_id)
        return total

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """
        Semantic search. Optionally filter to a specific document.
        """
        query_filter = None
        if document_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=query_filter,
        )

        return [
            {
                "score": round(hit.score, 4),
                "text": (hit.payload or {}).get("text", ""),
                "page_number": (hit.payload or {}).get("page_number", 0),
                "chunk_id": (hit.payload or {}).get("chunk_id", ""),
                "document_id": (hit.payload or {}).get("document_id"),
                "metadata": (hit.payload or {}).get("metadata", {}),
            }
            for hit in results.points
        ]

    def get_document_count(self) -> int:
        """How many points are indexed."""
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            return info.points_count
        except Exception:
            return 0