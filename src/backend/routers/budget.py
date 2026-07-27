import os
import tempfile
import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from ..config import config
from ..services.pdf_extractor import extract_raw_tables, extract_text_fallback
from ..services.deepseek_cleaner import structure_budget_rows, validate_budget_lines
from ..services.vector_store import upload_to_pinecone

router = APIRouter(prefix="/api/budget", tags=["budget"])

# In-memory job tracker (replace with DB in production)
jobs = {}


class IngestionStatus(BaseModel):
    job_id: str
    status: str  # "uploading", "extracting", "structuring", "validating", "uploading_to_vector_db", "complete", "failed"
    progress: float  # 0.0 to 1.0
    stats: Optional[dict] = None
    error: Optional[str] = None


@router.post("/upload", response_model=dict)
async def upload_budget_pdf(
    file: UploadFile = File(...),
):
    """
    Upload a county budget PDF for ingestion.
    
    1. Saves the file
    2. Extracts tables with pdfplumber
    3. Structures with DeepSeek
    4. Validates with DeepSeek
    5. Uploads to Pinecone vector DB
    
    Returns immediately with a job_id. Poll GET /api/budget/status/{job_id} for progress.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    # Check file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > config.MAX_PDF_SIZE_MB:
        raise HTTPException(400, f"File too large. Max {config.MAX_PDF_SIZE_MB}MB")

    # Save to temp file
    job_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, f"{job_id}.pdf")

    with open(pdf_path, "wb") as f:
        f.write(content)

    jobs[job_id] = {
        "status": "extracting",
        "progress": 0.0,
        "stats": {"filename": file.filename, "size_mb": round(size_mb, 2)},
    }

    # Run the full pipeline in the background
    import concurrent.futures
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_ingestion_pipeline_sync, job_id, pdf_path, temp_dir)


    return {
        "job_id": job_id,
        "status": "extracting",
        "message": f"Budget PDF '{file.filename}' ({size_mb:.1f}MB) uploaded. Ingestion started.",
        "poll_url": f"/api/budget/status/{job_id}",
    }


@router.get("/status/{job_id}", response_model=IngestionStatus)
async def get_ingestion_status(job_id: str):
    """Poll this endpoint to track ingestion progress."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    return IngestionStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        stats=job.get("stats"),
        error=job.get("error"),
    )
        
        
def _run_ingestion_pipeline_sync(job_id: str, pdf_path: str, temp_dir: str):
    """Synchronous version — runs in a background thread so it doesn't block the event loop."""
    print(f"🚀 Starting ingestion pipeline for job {job_id}...")
    try:
        # ── Stage 1: Extract ──
        jobs[job_id]["status"] = "extracting"
        jobs[job_id]["progress"] = 0.1
        print(f"📄 Extracting tables from PDF...")

        extraction_result = extract_raw_tables(pdf_path)
        print(f"   Extracted {extraction_result['total_rows_extracted']} rows from {extraction_result['total_pages']} pages")

        jobs[job_id]["stats"]["total_pages"] = extraction_result["total_pages"]
        jobs[job_id]["stats"]["pages_with_tables"] = extraction_result["pages_with_tables"]
        jobs[job_id]["stats"]["raw_rows"] = extraction_result["total_rows_extracted"]

        # ── Stage 2: Structure ──
        jobs[job_id]["status"] = "structuring"
        jobs[job_id]["progress"] = 0.3
        print(f"🧠 Structuring {extraction_result['total_rows_extracted']} rows with DeepSeek...")

        all_structured_lines = []
        table_pages = [p for p in extraction_result["pages"] if p["type"] == "table"]
        total_pages = len(table_pages)

        for i, page_data in enumerate(table_pages):
            if page_data["rows"]:
                print(f"   Page {page_data['page_num']} ({i+1}/{total_pages})...")
                structured = structure_budget_rows(page_data["rows"], page_data["page_num"])
                all_structured_lines.extend(structured)

            # Update progress
            progress = 0.3 + 0.3 * ((i + 1) / max(total_pages, 1))
            jobs[job_id]["progress"] = min(progress, 0.6)

        jobs[job_id]["stats"]["structured_lines"] = len(all_structured_lines)
        print(f"   Structured {len(all_structured_lines)} budget lines")

        # ── Stage 3: Validate ──
        jobs[job_id]["status"] = "validating"
        jobs[job_id]["progress"] = 0.7
        print(f"🔍 Validating {len(all_structured_lines)} lines...")

        validation = validate_budget_lines(all_structured_lines)
        valid_lines = validation.get("valid_lines", all_structured_lines)
        issues = validation.get("issues", [])

        jobs[job_id]["stats"]["valid_lines"] = len(valid_lines)
        jobs[job_id]["stats"]["issues_found"] = len(issues)
        print(f"   {len(valid_lines)} valid, {len(issues)} issues")

        # ── Stage 4: Upload to Pinecone ──
        jobs[job_id]["status"] = "uploading_to_vector_db"
        jobs[job_id]["progress"] = 0.85
        print(f"📤 Uploading {len(valid_lines)} vectors to Pinecone...")

        upload_result = upload_to_pinecone(valid_lines)
        jobs[job_id]["stats"]["uploaded_to_vectordb"] = upload_result["total_uploaded"]

        # ── Done ──
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["progress"] = 1.0
        print(f"✅ Job {job_id} complete! {upload_result['total_uploaded']} vectors uploaded.")

    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

    finally:
        try:
            os.remove(pdf_path)
            os.rmdir(temp_dir)
        except:
            pass