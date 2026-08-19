"""
PDF ingestion — parse and chunk county budget PDFs.
No LLM calls. Pure text extraction + chunking.
"""

import logging
import re
import uuid
from pathlib import Path

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

CHUNK_SIZE = 300
CHUNK_OVERLAP = 30


def parse_pdf(pdf_path: str | None) -> list[dict]:
    """
    Extract text from a county budget PDF.
    Returns list of { page_number, text } dicts.
    """
    if not pdf_path:
        raise ValueError("No PDF path provided")

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            # Also try to extract tables
            tables = [t for t in page.extract_tables() if t]
            if tables:
                for table in tables:
                    table_text = _table_to_text(table)
                    if table_text.strip():
                        text += "\n" + table_text

            if text.strip():
                pages.append({
                    "page_number": i,
                    "text": text.strip(),
                    # structured table rows for the line-item extractor
                    "tables": tables,
                })

    if not pages:
        raise ValueError(f"No text extracted from {pdf_path}")

    logger.info("Parsed %d pages from %s", len(pages), path.name)
    return pages


def _table_to_text(table: list[list[str | None]]) -> str:
    """Convert a pdfplumber table into readable text lines."""
    lines = []
    for row in table:
        if row and any(cell for cell in row):
            line = " | ".join(str(cell) if cell else "" for cell in row)
            lines.append(line)
    return "\n".join(lines)


def chunk_documents(pages: list[dict]) -> list[dict]:
    """
    Split PDF pages into overlapping text chunks for embedding.

    Returns list of { chunk_id, text, page_number } dicts.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    seen_texts = set()
    
    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]
        page_chunks = splitter.split_text(page_text)

        for chunk_text in page_chunks:
            cleaned = re.sub(r"\s+", " ", chunk_text).strip()
            if len(cleaned) < 30:
                continue
            norm = cleaned.lower()[:200]  # compare first 200 chars
            if norm in seen_texts:
                continue
            seen_texts.add(norm)
            
            chunks.append({
                "chunk_id": f"CH-{uuid.uuid4().hex[:8]}",
                "text": cleaned,
                "page_number": page_num,
            })

    logger.info("Created %d chunks from %d pages", len(chunks), len(pages))
    return chunks 