"""
Vector store — wraps Qdrant (local or remote) for budget & participation chunks.
"""

import logging
from pathlib import Path
import uuid as _uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..config import settings

logger = logging.getLogger(__name__)

BUDGET_COLLECTION = "budget_chunks"
PARTICIPATION_COLLECTION = "participation_chunks"


class VectorStore:
    """Qdrant vector store for budget & participation document chunks."""

    def __init__(self, path: str | Path | None = None, url: str | None = None):
        if settings.QDRANT_URL:
            self.client = QdrantClient(url=settings.QDRANT_URL)
            logger.info("Qdrant connected at: %s", settings.QDRANT_URL)
        else:
            store_path = str(path or settings.QDRANT_PATH)
            Path(store_path).mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=store_path)
            logger.info("Qdrant local store at: %s", store_path)

    # ── Collection helpers ─────────────────────────────────────────

    def _list_collections(self) -> list[str]:
        return [c.name for c in self.client.get_collections().collections]

    def collection_exists(self, name: str = BUDGET_COLLECTION) -> bool:
        return name in self._list_collections()

    def create_collection(
        self,
        vector_size: int,
        force: bool = False,
        name: str = BUDGET_COLLECTION,
    ):
        if self.collection_exists(name):
            if force:
                logger.info("Recreating collection '%s'", name)
                self.client.delete_collection(name)
            else:
                logger.info("Collection '%s' already exists", name)
                return

        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Created collection '%s' (dim=%d, distance=COSINE)", name, vector_size
        )

    def upsert_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        batch_size: int = 100,
        collection: str = BUDGET_COLLECTION,
        document_id: str | None = None,
    ) -> int:
        """Insert or update chunk embeddings into a Qdrant collection."""
        total = len(chunks)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_points = []
            for i in range(start, end):
                chunk = chunks[i]
                embedding = embeddings[i]
                payload = {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "page_number": chunk.get("page_number", 0),
                }
                if document_id:
                    payload["document_id"] = document_id
                if chunk.get("metadata"):
                    payload["metadata"] = chunk["metadata"]

                batch_points.append(
                    PointStruct(
                        id=str(_uuid.uuid4()),
                        vector=embedding,
                        payload=payload,
                    )
                )

            self.client.upsert(
                collection_name=collection,
                points=batch_points,
                wait=True,
            )
            logger.debug("Upserted batch %d–%d / %d", start + 1, end, total)

        logger.info("Upserted %d chunks into '%s'", total, collection)
        return total

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        collection: str = BUDGET_COLLECTION,
        document_id: str | None = None,
    ) -> list[dict]:
        """Semantic search over a collection."""
        query_filter = None
        if document_id:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            query_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )

        results = self.client.query_points(
            collection_name=collection,
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
                "document_id": (hit.payload or {}).get("document_id", ""),
                "metadata": (hit.payload or {}).get("metadata", {}),
            }
            for hit in results.points
        ]

    # ── Convenience ────────────────────────────────────────────────

    def budget_collection_exists(self) -> bool:
        return self.collection_exists(BUDGET_COLLECTION)

    def participation_collection_exists(self) -> bool:
        return self.collection_exists(PARTICIPATION_COLLECTION)