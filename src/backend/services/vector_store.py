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

PAYLOAD_KEYS = (
    "location", "ward", "subcounty", "sector", "sub_sector",
    "amount_ksh", "project_code",
)


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
                for key in PAYLOAD_KEYS:
                    val = chunk.get(key)
                    if val is not None and val != "":
                        payload[key] = val
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
        location: str | None = None,
        subcounty: str | None = None,
        sector: str | None = None,
    ) -> list[dict]:
        """Semantic search with optional hard filters (location/subcounty/sector)."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        must = []
        if document_id:
            must.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        if location:
            must.append(FieldCondition(key="location", match=MatchValue(value=location)))
        if subcounty:
            must.append(FieldCondition(key="subcounty", match=MatchValue(value=subcounty)))
        if sector:
            must.append(FieldCondition(key="sector", match=MatchValue(value=sector)))

        query_filter = Filter(must=must) if must else None

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
                "location": (hit.payload or {}).get("location", ""),
                "ward": (hit.payload or {}).get("ward", ""),
                "subcounty": (hit.payload or {}).get("subcounty", ""),
                "sector": (hit.payload or {}).get("sector", ""),
                "sub_sector": (hit.payload or {}).get("sub_sector", ""),
                "amount_ksh": (hit.payload or {}).get("amount_ksh"),
                "project_code": (hit.payload or {}).get("project_code", ""),
                "metadata": (hit.payload or {}).get("metadata", {}),
            }
            for hit in results.points
        ]

    def scroll_all(
        self,
        collection: str = BUDGET_COLLECTION,
        limit: int = 10000,
    ) -> list[dict]:
        """Scroll all points (payload only) from a collection."""
        points = []
        offset = None
        while True:
            pts, nxt = self.client.scroll(
                collection_name=collection,
                with_payload=True,
                with_vectors=False,
                limit=limit,
                offset=offset,
            )
            for p in pts:
                pl = p.payload or {}
                points.append({
                    "chunk_id": pl.get("chunk_id", ""),
                    "text": pl.get("text", ""),
                    "location": pl.get("location", ""),
                    "ward": pl.get("ward", ""),
                    "subcounty": pl.get("subcounty", ""),
                    "sector": pl.get("sector", ""),
                    "sub_sector": pl.get("sub_sector", ""),
                    "amount_ksh": pl.get("amount_ksh"),
                    "page_number": pl.get("page_number", 0),
                    "document_id": pl.get("document_id", ""),
                })
            if nxt is None:
                break
            offset = nxt
        return points

    # ── Convenience ────────────────────────────────────────────────

    def budget_collection_exists(self) -> bool:
        return self.collection_exists(BUDGET_COLLECTION)

    def participation_collection_exists(self) -> bool:
        return self.collection_exists(PARTICIPATION_COLLECTION)