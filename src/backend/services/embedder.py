"""
Embedding service — wraps Sentence Transformers with batch support.
Uses all-MiniLM-L6-v2 (384-dim) by default.
Supports Cohere and OpenAI as optional backends.
"""
import os
import logging

logger = logging.getLogger(__name__)

BACKEND = os.getenv("EMBEDDING_BACKEND", "local").strip().lower()
EMBEDDING_DIM = 384  # default, overridden per backend

# ──────────────────────────────────────────────────────────────────
# Backend: LOCAL — sentence-transformers (free, offline)
# ──────────────────────────────────────────────────────────────────
if BACKEND == "local":
    from sentence_transformers import SentenceTransformer

    class EmbeddingService:
        """Lazy-loading Sentence Transformer wrapper with batch support."""

        def __init__(self, model_name: str | None = None):
            self.model_name = model_name or "all-MiniLM-L6-v2"
            self.model = None
            self._vector_size: int | None = None

        def _load(self):
            if self.model is not None:
                return
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
            test_vec = self.model.encode("test", show_progress_bar=False)
            self._vector_size = len(test_vec)

        @property
        def vector_size(self) -> int:
            if self._vector_size is None:
                self._load()
            return self._vector_size

        def embed_texts(
            self, texts: list[str], show_progress: bool = True
        ) -> list[list[float]]:
            """Batch-embed a list of texts. Fast!"""
            self._load()
            embeddings = self.model.encode(
                texts,
                show_progress_bar=show_progress,
                normalize_embeddings=True,
            )
            return embeddings.tolist()

        def embed_query(self, query: str) -> list[float]:
            """Embed a single search query."""
            self._load()
            embedding = self.model.encode(
                query,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return embedding.tolist()

    EMBEDDING_DIM = 384

# ──────────────────────────────────────────────────────────────────
# Backend: COHERE
# ──────────────────────────────────────────────────────────────────
elif BACKEND == "cohere":
    import cohere

    class EmbeddingService:
        def __init__(self, model_name: str | None = None):
            self.model_name = "embed-english-v3.0"
            self._client = None

        def _load(self):
            if self._client is not None:
                return
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise RuntimeError("COHERE_API_KEY not set")
            self._client = cohere.ClientV2(api_key=api_key)

        @property
        def vector_size(self) -> int:
            return 1024

        def embed_texts(self, texts, show_progress=True):
            self._load()
            all_embeddings = []
            batch_size = 96
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                resp = self._client.embed(
                    model=self.model_name,
                    texts=batch,
                    input_type="search_document",
                    embedding_types=["float"],
                )
                all_embeddings.extend(resp.embeddings.float)
            return all_embeddings

        def embed_query(self, query):
            self._load()
            resp = self._client.embed(
                model=self.model_name,
                texts=[query],
                input_type="search_query",
                embedding_types=["float"],
            )
            return resp.embeddings.float[0]

    EMBEDDING_DIM = 1024

# ──────────────────────────────────────────────────────────────────
# Backend: OPENAI
# ──────────────────────────────────────────────────────────────────
elif BACKEND == "openai":
    import openai

    class EmbeddingService:
        def __init__(self, model_name: str | None = None):
            self.model_name = "text-embedding-3-small"
            self._client = None

        def _load(self):
            if self._client is not None:
                return
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            self._client = openai.OpenAI(api_key=api_key)

        @property
        def vector_size(self) -> int:
            return 1536

        def embed_texts(self, texts, show_progress=True):
            self._load()
            resp = self._client.embeddings.create(
                model=self.model_name, input=texts
            )
            return [d.embedding for d in resp.data]

        def embed_query(self, query):
            self._load()
            resp = self._client.embeddings.create(
                model=self.model_name, input=query
            )
            return resp.data[0].embedding

    EMBEDDING_DIM = 1536

else:
    # Fallback to local
    from sentence_transformers import SentenceTransformer

    class EmbeddingService:
        def __init__(self, model_name=None):
            self.model_name = "all-MiniLM-L6-v2"
            self.model = SentenceTransformer(self.model_name)
            self._vector_size = 384

        @property
        def vector_size(self):
            return self._vector_size

        def embed_texts(self, texts, show_progress=True):
            return self.model.encode(
                texts, show_progress_bar=show_progress, normalize_embeddings=True
            ).tolist()

        def embed_query(self, query):
            return self.model.encode(
                query, show_progress_bar=False, normalize_embeddings=True
            ).tolist()

    EMBEDDING_DIM = 384