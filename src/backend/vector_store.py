"""
Vector store — wraps Qdrant (local file-based mode) for budget chunk storage.
"""
import logging
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────
COLLECTION_NAME = "budget_chunks"
QDRANT_PATH = Path(__file__).resolve().parents[2] / "data" / "qdrant_storage"


class VectorStore:
    """Qdrant local vector store for budget document chunks."""

    def __init__(self, path: str | Path | None = None):
        store_path = str(path or QDRANT_PATH)
        Path(store_path).mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=store_path)
        logger.info("Qdrant local store initialized at: %s", store_path)

    def collection_exists(self) -> bool:
        """Check whether the budget collection already exists."""
        collections = [
            c.name
            for c in self.client.get_collections().collections
        ]
        return COLLECTION_NAME in collections

    def create_collection(self, vector_size: int, force: bool = False):
        """Create (or recreate) the collection."""
        if self.collection_exists():
            if force:
                logger.info("Deleting existing collection '%s'", COLLECTION_NAME)
                self.client.delete_collection(COLLECTION_NAME)
            else:
                logger.info("Collection '%s' already exists", COLLECTION_NAME)
                return

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Created collection '%s' (vector_size=%d, distance=COSINE)",
            COLLECTION_NAME,
            vector_size,
        )

    def upsert_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        batch_size: int = 100,
    ) -> int:
        """
        Insert or update chunk embeddings into Qdrant.

        chunks: list of { chunk_id, text, page_number, metadata }
        embeddings: parallel list of embedding vectors

        Returns total number of points upserted.
        """
        total = len(chunks)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_points = []
            for i in range(start, end):
                chunk = chunks[i]
                embedding = embeddings[i]
                batch_points.append(
                    PointStruct(
                        id=i,  # numeric ID for efficient lookup
                        vector=embedding,
                        payload={
                            "chunk_id": chunk["chunk_id"],
                            "text": chunk["text"],
                            "page_number": chunk["page_number"],
                            "metadata": chunk.get("metadata", {}),
                        },
                    )
                )

            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch_points,
                wait=True,
            )
            logger.debug(
                "Upserted batch %d–%d / %d", start + 1, end, total
            )

        logger.info("Upserted %d chunks into '%s'", total, COLLECTION_NAME)
        return total

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """
        Semantic search over budget chunks.

        Returns list of { score, text, page_number, chunk_id, metadata }
        """
        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "score": round(hit.score, 4),
                "text": (hit.payload or {}).get("text", ""),
                "page_number": (hit.payload or {}).get("page_number", 0),
                "chunk_id": (hit.payload or {}).get("chunk_id", ""),
                "metadata": (hit.payload or {}).get("metadata", {}),
            }
            for hit in results.points
        ]
