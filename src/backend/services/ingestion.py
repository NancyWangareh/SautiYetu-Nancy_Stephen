"""
PDF ingestion — parse budget PDF and chunk text for embedding.
Replaces the old DeepSeek table-structuring approach.
Fast: ~5 seconds for a 200-page PDF.
"""
import logging
from pathlib import Path
from typing import List, Dict

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def parse_pdf(file_path: str | Path) -> List[Dict]:
    """
    Extract text from every page of the budget PDF.
    Simple text extraction — no table parsing needed.

    Returns: [{ page_number: int, text: str }, ...]
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page_number": i, "text": text.strip()})
            if i % 50 == 0:
                logger.info("Parsed page %d/%d", i, total)

    logger.info("Parsed %d pages total", len(pages))
    return pages


def chunk_documents(
    pages: List[Dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Dict]:
    """
    Split pages into overlapping chunks for embedding.

    Returns: [{ chunk_id, text, page_number, metadata }, ...]
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks: List[Dict] = []
    for page in pages:
        page_num = page["page_number"]
        text = page["text"]
        if not text.strip():
            continue

        page_chunks = splitter.split_text(text)
        for j, chunk_text in enumerate(page_chunks):
            chunks.append({
                "chunk_id": f"p{page_num}_c{j}",
                "text": chunk_text,
                "page_number": page_num,
                "metadata": {"source_page": page_num, "chunk_index": j},
            })

    logger.info("Created %d chunks from %d pages", len(chunks), len(pages))
    return chunks