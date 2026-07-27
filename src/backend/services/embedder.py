"""
Pluggable embedding service for SautiYetu.

Switch between backends by setting EMBEDDING_BACKEND in .env:
  - "local"   → sentence-transformers (free, runs on CPU, no API keys)
  - "cohere"  → Cohere Embed API (managed, 1024-dim)
  - "openai"  → OpenAI text-embedding-3-small (managed, 1536-dim)

Exports:
  - embed_text(text: str) -> list[float]
  - EMBEDDING_DIM: int  (must match Pinecone index dimension!)
"""

import os
from ..config import config

BACKEND = os.getenv("EMBEDDING_BACKEND", "local").strip().lower()

# ──────────────────────────────────────────────────────────────────
# Backend: LOCAL — sentence-transformers (free, offline)
# Model: all-MiniLM-L6-v2 — 384 dimensions, ~80MB
# First call downloads the model (~20-30s), then cached in memory.
# ──────────────────────────────────────────────────────────────────
if BACKEND == "local":
    from sentence_transformers import SentenceTransformer

    _model = None

    def _get_model():
        global _model
        if _model is None:
            print("⏳ Loading embedding model (all-MiniLM-L6-v2)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Embedding model ready.")
        return _model

    def embed_text(text: str):
        """
        Generate a 384-dim normalized embedding vector.
        Handles empty/short text gracefully.
        """
        if not text or not text.strip():
            text = "empty"
        return _get_model().encode(
            text.strip(),
            normalize_embeddings=True,
        ).tolist()

    EMBEDDING_DIM = 384

# ──────────────────────────────────────────────────────────────────
# Backend: COHERE — Cohere Embed API
# Model: embed-english-v3.0 — 1024 dimensions
# Free trial key: dashboard.cohere.com
# ──────────────────────────────────────────────────────────────────
elif BACKEND == "cohere":
    import cohere

    _co = None

    def _get_client():
        global _co
        if _co is None:
            api_key = os.getenv("COHERE_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "COHERE_API_KEY not set. Add it to .env or switch EMBEDDING_BACKEND=local"
                )
            _co = cohere.ClientV2(api_key=api_key)
        return _co

    def embed_text(text: str):
        if not text or not text.strip():
            text = "empty"
        resp = _get_client().embed(
            model="embed-english-v3.0",
            texts=[text.strip()],
            input_type="search_query",       # for citizen queries
            embedding_types=["float"],
        )
        return resp.embeddings.float[0]

    EMBEDDING_DIM = 1024

# ──────────────────────────────────────────────────────────────────
# Backend: OPENAI — text-embedding-3-small
# 1536 dimensions, $0.02 per 1M tokens
# ──────────────────────────────────────────────────────────────────
elif BACKEND == "openai":
    import openai

    _client = None

    def _get_client():
        global _client
        if _client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY not set. Add it to .env or switch EMBEDDING_BACKEND=local"
                )
            _client = openai.OpenAI(api_key=api_key)
        return _client

    def embed_text(text: str):
        if not text or not text.strip():
            text = "empty"
        resp = _get_client().embeddings.create(
            model="text-embedding-3-small",
            input=text.strip(),
        )
        return resp.data[0].embedding

    EMBEDDING_DIM = 1536

else:
    raise ValueError(
        f"Unknown EMBEDDING_BACKEND='{BACKEND}'. "
        "Set to 'local', 'cohere', or 'openai' in your .env file."
    )