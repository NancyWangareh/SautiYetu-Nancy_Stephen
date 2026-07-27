"""
Embedding service — wraps Sentence Transformers for budget document embeddings.

Uses intfloat/multilingual-e5-small (384-dim) which handles English +
Swahili/local terms common in Kenyan budget documents.

Falls back to all-MiniLM-L6-v2 if the multilingual model is unavailable.
"""
import logging

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────
PRIMARY_MODEL = "intfloat/multilingual-e5-small"
FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# E5 models require prefixing: "query: " for queries, "passage: " for docs
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "
USES_PREFIX = "e5" in PRIMARY_MODEL.lower()


class EmbeddingService:
    """Lazy-loading Sentence Transformer wrapper."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or PRIMARY_MODEL
        self.model = None
        self._vector_size: int | None = None

    def _load(self):
        """Lazy-load the model on first use."""
        if self.model is not None:
            return

        from sentence_transformers import SentenceTransformer

        try:
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
        except Exception:
            if self.model_name != FALLBACK_MODEL:
                logger.warning(
                    "Failed to load %s, falling back to %s",
                    self.model_name,
                    FALLBACK_MODEL,
                )
                self.model_name = FALLBACK_MODEL
                self.model = SentenceTransformer(FALLBACK_MODEL)
            else:
                raise

        # Determine vector size from a test encoding
        test_vec = self.model.encode("test", show_progress_bar=False)
        self._vector_size = len(test_vec)

    @property
    def vector_size(self) -> int:
        if self._vector_size is None:
            self._load()
        assert self._vector_size is not None
        return self._vector_size

    def embed_texts(self, texts: list[str], show_progress: bool = True) -> list[list[float]]:
        """Batch-embed a list of document texts."""
        self._load()
        if USES_PREFIX:
            texts = [f"{PASSAGE_PREFIX}{t}" for t in texts]
        embeddings = self.model.encode(
            texts,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single search query."""
        self._load()
        if USES_PREFIX:
            query = f"{QUERY_PREFIX}{query}"
        embedding = self.model.encode(
            query,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embedding.tolist()
