from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .db.database import get_db
from .services.embedder import EmbeddingService
from .services.vector_store import VectorStore
from .services.classifier import ClassifierService
from .services.matcher import MatcherService

_embedder: EmbeddingService | None = None
_store: VectorStore | None = None
_classifier: ClassifierService | None = None
_matcher: MatcherService | None = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def get_classifier() -> ClassifierService:
    global _classifier
    if _classifier is None:
        _classifier = ClassifierService(get_embedder())
    return _classifier


def get_matcher() -> MatcherService:
    global _matcher
    if _matcher is None:
        _matcher = MatcherService(get_embedder(), get_vector_store())
    return _matcher