"""
Budget PDF upload & management.
Fast pipeline: Parse → Chunk → Batch Embed → Qdrant.
Supports multiple docs + duplicate detection.
"""
import os
import hashlib
import tempfile
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..config import config
from ..db.database import get_db
from ..db.models import BudgetDocument, DocumentStatus
from ..services.ingestion import parse_pdf, chunk_documents
from ..services.embedder import EmbeddingService
from ..services.vector_store import VectorStore

router = APIRouter(prefix="/api/budget", tags=["budget"])

jobs = {}


class IngestionStatus(BaseModel):
    job_id: str
    document_id: str
    status: str
    progress: float
    stats: Optional[dict] = None
    error: Optional[str] = None


# ── Upload ────────────────────────────────────────────────────────────

@router.post("/upload", response_model=dict)
async def upload_budget_pdf(
    file: UploadFile = File(...),
    fiscal_year: str = "2024/25",
    db: AsyncSession = Depends(get_db),
):
    """Upload a county budget PDF. Detects duplicates via file hash."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > config.MAX_PDF_SIZE_MB:
        raise HTTPException(400, f"File too large. Max {config.MAX_PDF_SIZE_MB}MB")

    # Duplicate detection — only block if doc is already "ready"
    file_hash = hashlib.sha256(content).hexdigest()
    existing = await db.execute(
        select(BudgetDocument).where(BudgetDocument.file_hash == file_hash)
    )
    existing_doc = existing.scalar_one_or_none()
    if existing_doc:
        if existing_doc.status == DocumentStatus.ready:
            raise HTTPException(
                400,
                f"Already uploaded as '{existing_doc.filename}' "
                f"on {existing_doc.uploaded_at.strftime('%Y-%m-%d')}. "
                f"ID: {existing_doc.id}",
            )
        elif existing_doc.status in (DocumentStatus.uploading, DocumentStatus.failed):
            print(f"⚠️ Removing stuck record {existing_doc.id} (status={existing_doc.status})")
            await db.delete(existing_doc)
            await db.commit()

    # Create document record
    document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    doc = BudgetDocument(
        id=document_id, filename=file.filename, file_hash=file_hash,
        fiscal_year=fiscal_year, size_mb=round(size_mb, 2),
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

    jobs[job_id] = {
        "document_id": document_id,
        "status": "parsing",
        "progress": 0.0,
        "stats": {"filename": file.filename, "size_mb": round(size_mb, 2)},
    }

    # Run in background — capture the main loop HERE (not in the thread!)
    import concurrent.futures
    import asyncio
    main_loop = asyncio.get_running_loop()
    main_loop.run_in_executor(None, _ingest, job_id, document_id, pdf_path, temp_dir, main_loop)

    return {
        "job_id": job_id,
        "document_id": document_id,
        "status": "parsing",
        "message": f"Ingestion started for '{file.filename}'",
        "poll_url": f"/api/budget/status/{job_id}",
    }


# ── Status ────────────────────────────────────────────────────────────

@router.get("/status/{job_id}", response_model=IngestionStatus)
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    j = jobs[job_id]
    return IngestionStatus(
        job_id=job_id, document_id=j.get("document_id", ""),
        status=j["status"], progress=j["progress"],
        stats=j.get("stats"), error=j.get("error"),
    )


# ── List / Get / Delete Documents ─────────────────────────────────────

@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all uploaded budget PDFs."""
    result = await db.execute(
        select(BudgetDocument).order_by(desc(BudgetDocument.uploaded_at))
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id, "filename": d.filename, "fiscal_year": d.fiscal_year,
            "status": d.status, "size_mb": d.size_mb,
            "total_pages": d.total_pages, "total_chunks": d.total_chunks,
            "uploaded_at": d.uploaded_at.isoformat(),
            "completed_at": d.completed_at.isoformat() if d.completed_at else None,
            "error_message": d.error_message,
        }
        for d in docs
    ]


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetDocument).where(BudgetDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id, "filename": doc.filename, "fiscal_year": doc.fiscal_year,
        "status": doc.status, "size_mb": doc.size_mb,
        "total_pages": doc.total_pages, "total_chunks": doc.total_chunks,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "completed_at": doc.completed_at.isoformat() if doc.completed_at else None,
        "error_message": doc.error_message,
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetDocument).where(BudgetDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.status = DocumentStatus.archived
    doc.error_message = f"Archived on {datetime.utcnow().isoformat()}"
    await db.commit()
    return {"message": f"Document {document_id} archived", "id": document_id}


# ── Ingest Pipeline (runs in background thread) ───────────────────────

def _ingest(job_id: str, document_id: str, pdf_path: str, temp_dir: str, main_loop):
    """
    Fast pipeline: parse → chunk → embed → qdrant. No LLM calls.
    Runs in a background thread. DB updates via main_loop parameter.
    """
    import traceback
    import asyncio

    try:
        # ── Stage 1: Parse ──
        jobs[job_id]["status"] = "parsing"
        jobs[job_id]["progress"] = 0.1
        print(f"📄 Parsing PDF...")
        pages = parse_pdf(pdf_path)
        non_empty = [p for p in pages if p["text"].strip()]
        jobs[job_id]["stats"]["total_pages"] = len(pages)
        jobs[job_id]["stats"]["pages_with_text"] = len(non_empty)
        print(f"   Parsed {len(pages)} pages ({len(non_empty)} with text)")

        # ── Stage 2: Chunk ──
        jobs[job_id]["status"] = "chunking"
        jobs[job_id]["progress"] = 0.3
        print(f"✂️ Chunking...")
        chunks = chunk_documents(pages)
        if not chunks:
            raise ValueError("No text extracted from PDF")
        jobs[job_id]["stats"]["chunks_created"] = len(chunks)
        print(f"   Created {len(chunks)} chunks")

        # ── Stage 3: Embed (batch) ──
        jobs[job_id]["status"] = "embedding"
        jobs[job_id]["progress"] = 0.5
        print(f"🧠 Embedding {len(chunks)} chunks...")
        embedder = EmbeddingService()
        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed_texts(texts, show_progress=True)
        jobs[job_id]["stats"]["vector_dim"] = embedder.vector_size
        print(f"   Embedded {len(embeddings)} vectors (dim={embedder.vector_size})")

        # ── Stage 4: Store in Qdrant ──
        jobs[job_id]["status"] = "storing"
        jobs[job_id]["progress"] = 0.8
        print(f"💾 Storing in Qdrant...")
        store = VectorStore()
        if not store.collection_exists():
            store.create_collection(embedder.vector_size, force=False)
        count = store.upsert_chunks(chunks, embeddings, document_id=document_id)
        jobs[job_id]["stats"]["vectors_stored"] = count
        print(f"   Stored {count} vectors (doc={document_id})")

        # ── Update DB via the passed-in main_loop ──
        async def _update_db():
            from ..db.database import async_session
            from ..db.models import BudgetDocument, DocumentStatus
            from sqlalchemy import select

            async with async_session() as session:
                result = await session.execute(
                    select(BudgetDocument).where(BudgetDocument.id == document_id)
                )
                doc = result.scalar_one()
                doc.total_pages = len(pages)
                doc.total_chunks = count
                doc.status = DocumentStatus.ready
                doc.completed_at = __import__("datetime").datetime.utcnow()
                await session.commit()
                print(f"✅ DB updated: doc {document_id} ready ({count} chunks)")

        future = asyncio.run_coroutine_threadsafe(_update_db(), main_loop)
        future.result(timeout=10)

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["progress"] = 1.0
        print(f"✅ Job {job_id} complete! {count} vectors stored.")

    except Exception as e:
        traceback.print_exc()
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"❌ Job {job_id} failed: {e}")

        async def _update_db_failed():
            from ..db.database import async_session
            from ..db.models import BudgetDocument, DocumentStatus
            from sqlalchemy import select

            try:
                async with async_session() as session:
                    result = await session.execute(
                        select(BudgetDocument).where(BudgetDocument.id == document_id)
                    )
                    doc = result.scalar_one()
                    doc.status = DocumentStatus.failed
                    doc.error_message = str(e)[:500]
                    await session.commit()
            except Exception as db_err:
                print(f"⚠️ Could not update DB with failure: {db_err}")

        try:
            future = asyncio.run_coroutine_threadsafe(_update_db_failed(), main_loop)
            future.result(timeout=5)
        except Exception:
            pass

    finally:
        try:
            os.remove(pdf_path)
            os.rmdir(temp_dir)
        except Exception:
            pass