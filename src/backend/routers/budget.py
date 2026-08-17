"""
Budget PDF upload, search, and management.
"""

import asyncio
import hashlib
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from qdrant_client.models import Filter, FieldCondition, MatchValue

from ..config import settings
from ..db.database import get_db
from ..db.models import BudgetDocument, DocumentStatus
from ..schemas.budget import (
    SearchRequest, SimplifyRequest, SimplifyResponse,
    DocumentResponse, IngestionStatus,
)
from ..services.line_item_extractor import extract_line_items
from ..db.models import BudgetLineItem
from ..dependencies import get_embedder, get_vector_store
from ..services.embedder import EmbeddingService
from ..services.vector_store import VectorStore
from ..services.ingestion import parse_pdf, chunk_documents
from ..services.simplifier import simplify_budget_line, simplify_with_llm

MIN_LINE_ITEMS = 20   # below this, fall back to raw-text chunking

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/budget", tags=["budget"])


# In-memory job tracker during ingestion (per-process, acceptable for async workers)
_jobs: dict = {}

def _ingest_background(job_id, document_id, pdf_path, embedder, store, loop, budget_type="proposed", fiscal_year="2024/25"):
    """Run ingestion in background: parse → chunk → embed → store.
    
    embedder and store are the app-level singletons — do NOT create new instances.
    """
    import asyncio

    try:
        _jobs[job_id]["status"] = "parsing"
        _jobs[job_id]["progress"] = 0.1
        pages = parse_pdf(pdf_path)
        _jobs[job_id]["stats"]["total_pages"] = len(pages)

        _jobs[job_id]["status"] = "chunking"
        _jobs[job_id]["progress"] = 0.3
        chunks = chunk_documents(pages)
        if not chunks:
            raise ValueError("No text extracted from PDF")
        _jobs[job_id]["stats"]["chunks_created"] = len(chunks)

        _jobs[job_id]["status"] = "embedding"
        _jobs[job_id]["progress"] = 0.5
        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts, show_progress=True)
        _jobs[job_id]["stats"]["vector_dim"] = embedder.vector_size

        _jobs[job_id]["status"] = "indexing"
        _jobs[job_id]["progress"] = 0.8

        line_items = extract_line_items(pages, document_id, budget_type, fiscal_year)
        count = 0
        if len(line_items) >= MIN_LINE_ITEMS:
            count = len(line_items)
            asyncio.run_coroutine_threadsafe(
                _index_line_items(document_id, pages, budget_type, fiscal_year, embedder, store),
                loop,
            )
        else:
            # Fallback: raw text chunks (legacy behavior)
            collection = "budget_enacted" if budget_type == "enacted" else "budget_proposed"
            if not store.collection_exists(collection):
                store.create_collection(embedder.vector_size, force=False, name=collection)
            count = store.upsert_chunks(chunks, embeddings, document_id=document_id, collection=collection)
            _jobs[job_id]["stats"]["vectors_stored"] = count

        _jobs[job_id]["progress"] = 1.0

        # Mark document as ready in DB
        async def _mark_ready():
            from ..db.database import async_session
            from datetime import datetime as _dt
            async with async_session() as session:
                result = await session.execute(
                    select(BudgetDocument).where(BudgetDocument.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.ready
                    doc.total_pages = len(pages)
                    doc.total_chunks = count
                    doc.completed_at = _dt.utcnow()
                    await session.commit()
                    logger.info("DB updated: doc %s → ready (%d chunks)", document_id, count)
                    _jobs[job_id]["status"] = "complete"
                    _jobs[job_id]["progress"] = 1.0

        asyncio.run_coroutine_threadsafe(_mark_ready(), loop)
        logger.info("Job %s complete: %d vectors stored", job_id, count)

    except Exception as e:
        logger.exception("Job %s failed", job_id)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)[:500]

        async def _mark_failed():
            from ..db.database import async_session
            async with async_session() as session:
                result = await session.execute(
                    select(BudgetDocument).where(BudgetDocument.id == document_id)
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.failed
                    doc.error_message = str(e)[:500]
                    await session.commit()

        try:
            asyncio.run_coroutine_threadsafe(_mark_failed(), loop)
        except Exception:
            pass
        
        
# ── Upload ────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_budget_pdf(
    file: UploadFile = File(...),
    fiscal_year: str = Query(),
    budget_type: str = Query(),
    db: AsyncSession = Depends(get_db),
):
    """Upload a county budget PDF for ingestion."""
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_PDF_SIZE_MB:
        raise HTTPException(400, f"File too large. Max {settings.MAX_PDF_SIZE_MB}MB")

    # Duplicate detection
    file_hash = hashlib.sha256(content).hexdigest()
    existing = await db.execute(
        select(BudgetDocument).where(BudgetDocument.file_hash == file_hash)
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc:
        if existing_doc.status == DocumentStatus.ready:
            raise HTTPException(
                400,
                f"Already uploaded as '{existing_doc.filename}' on "
                f"{existing_doc.uploaded_at.strftime('%Y-%m-%d')}. ID: {existing_doc.id}",
            )
        elif existing_doc.status in (DocumentStatus.uploading, DocumentStatus.failed):
            await db.delete(existing_doc)
            await db.commit()

    # Create document record
    document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    doc = BudgetDocument(
        id=document_id,
        filename=file.filename,
        file_hash=file_hash,
        fiscal_year=fiscal_year,
        budget_type=budget_type,
        size_mb=round(size_mb, 2),
        status=DocumentStatus.uploading,
    )
    db.add(doc)
    await db.commit()

    # Save temp file
    job_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, f"{job_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(content)

    _jobs[job_id] = {
        "document_id": document_id,
        "status": "parsing",
        "progress": 0.0,
        "stats": {"filename": file.filename, "size_mb": round(size_mb, 2)},
    }

    # Run in background — reuse existing singletons, don't create new VectorStore
    loop = asyncio.get_running_loop()
    embedder = get_embedder()
    store = get_vector_store()
    loop.run_in_executor(None, _ingest_background, job_id, document_id, pdf_path, embedder, store, loop, budget_type, fiscal_year)

    return {
        "job_id": job_id,
        "document_id": document_id,
        "status": "parsing",
        "message": f"Ingestion started for '{file.filename}'",
        "poll_url": f"/api/budget/status/{job_id}",
    }


@router.get("/status/{job_id}", response_model=IngestionStatus)
async def get_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")
    j = _jobs[job_id]
    return IngestionStatus(
        job_id=job_id,
        document_id=j.get("document_id", ""),
        status=j["status"],
        progress=j["progress"],
        stats=j.get("stats"),
        error=j.get("error"),
    )


# ── Search ────────────────────────────────────────────────────────────────

@router.post("/search")
async def search_budget(
    payload: SearchRequest,
    embedder: EmbeddingService = Depends(get_embedder),
    store: VectorStore = Depends(get_vector_store),
):
    """Semantic search over budget document chunks (enacted first, then proposed)."""
    collection = None
    if store.collection_exists("budget_enacted"):
        collection = "budget_enacted"
    elif store.collection_exists("budget_proposed"):
        collection = "budget_proposed"

    if not collection:
        raise HTTPException(400, "Budget index not available. Upload a budget PDF first.")

    query_vector = embedder.embed_query(payload.query)
    hits = store.search(query_vector, top_k=payload.top_k, collection=collection)

    return {
        "results": [
            {
                "text": h["text"],
                "score": h["score"],
                "page_number": h.get("page_number", 0),
                "chunk_id": h.get("chunk_id", ""),
                "document_id": h.get("document_id", ""),
            }
            for h in hits
        ],
        "collection": collection,
        "query": payload.query,
    }
# ── Simplify ──────────────────────────────────────────────────────────────

@router.post("/simplify", response_model=SimplifyResponse)
async def simplify_budget(payload: SimplifyRequest):
    """Translate a complex budget line into plain language."""
    if settings.DEEPSEEK_API_KEY:
        result = simplify_with_llm(payload.text)
    else:
        result = simplify_budget_line(payload.text)

    return SimplifyResponse(
        original=payload.text,
        simplified=result["simplified"],
        key_points=result.get("key_points", result.get("keyPoints", [])),
        category=result["category"],
    )


# ── Documents CRUD ────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetDocument).order_by(desc(BudgetDocument.uploaded_at))
    )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id,
            filename=d.filename,
            fiscal_year=d.fiscal_year,
            budget_type=d.budget_type,
            status=d.status.value,
            size_mb=d.size_mb,
            total_pages=d.total_pages,
            total_chunks=d.total_chunks,
            uploaded_at=d.uploaded_at.isoformat(),
            completed_at=d.completed_at.isoformat() if d.completed_at else None,
            error_message=d.error_message,
        )
        for d in docs
    ]

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetDocument).where(BudgetDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete vectors from both collections
    store = get_vector_store()
    selector = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    for coll in ("budget_proposed", "budget_enacted"):
        if store.collection_exists(coll):
            store.client.delete(collection_name=coll, points_selector=selector)

    await db.delete(doc)
    await db.commit()
    return {"message": f"Document {document_id} deleted", "id": document_id}

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetDocument).where(BudgetDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return DocumentResponse(
        id=doc.id, filename=doc.filename, fiscal_year=doc.fiscal_year,
        budget_type=doc.budget_type,          # ← add this
        status=doc.status.value, size_mb=doc.size_mb,
        total_pages=doc.total_pages, total_chunks=doc.total_chunks,
        uploaded_at=doc.uploaded_at.isoformat(),
        completed_at=doc.completed_at.isoformat() if doc.completed_at else None,
        error_message=doc.error_message,
    )


async def _index_line_items(document_id, pages, budget_type, fiscal_year, embedder, store):
    """Classify + embed + store structured line items with location/sector."""
    import asyncio
    from ..db.database import async_session
    from ..db.models import BudgetLineItem
    from ..dependencies import get_classifier
    from ..services.geo import normalize_location
    from ..services.line_item_extractor import extract_line_items, line_items_to_chunks, build_search_text

    items = extract_line_items(pages, document_id, budget_type, fiscal_year)
    if not items:
        logger.warning("No structured line items extracted for %s", document_id)
        return

    # 1. Normalize location → ward/subcounty
    for it in items:
        loc = normalize_location(it.get("location"))
        it["subcounty"] = loc["subcounty"] if loc else None
        it["ward"] = loc["ward"] if loc else None

    # 2. Classify sectors (one batched LLM call for the whole document)
    classifier = get_classifier()
    texts = [build_search_text(i) for i in items]
    cls = await classifier.classify_budget_lines(texts)
    for it, c in zip(items, cls):
        it["sector"] = c.get("sector")
        it["sub_sector"] = c.get("sub_sector")

    # 3. Embed + store enriched line items in Qdrant
    chunks = line_items_to_chunks(items)
    chunk_texts = [c["text"] for c in chunks]
    embeddings = await asyncio.to_thread(embedder.embed_texts, chunk_texts, False)
    collection = "budget_enacted" if budget_type == "enacted" else "budget_proposed"
    if not store.collection_exists(collection):
        store.create_collection(embedder.vector_size, force=False, name=collection)
    await asyncio.to_thread(
        store.upsert_chunks, chunks, embeddings, 100, collection, document_id
    )

    # 4. Persist line items (now with sector/sub_sector/subcounty)
    async with async_session() as session:
        for it in items:
            session.add(BudgetLineItem(
                document_id=document_id,
                budget_type=budget_type,
                fiscal_year=fiscal_year,
                page_number=it.get("page_number"),
                s_no=it.get("s_no"),
                project_code=it.get("project_code"),
                project_name=it.get("project_name"),
                description=it.get("description"),
                location=it.get("location"),
                approved_amount=it.get("approved_amount"),
                revised_i_amount=it.get("revised_i_amount"),
                revised_ii_amount=it.get("revised_ii_amount"),
                sector=it.get("sector"),
                sub_sector=it.get("sub_sector"),
                source_text=it.get("source_text"),
            ))
        await session.commit()

    logger.info("Indexed %d line items for doc %s (type=%s)", len(chunks), document_id, budget_type)