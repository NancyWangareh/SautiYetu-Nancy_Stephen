"""
PDF ingestion — parse budget PDF with pdfplumber and chunk with LangChain.
"""
from pathlib import Path

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Config ───────────────────────────────────────────────────────────────
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Default PDF path (relative to project root)
DEFAULT_PDF = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "NAIROBI-CITY-COUNTY-SUPPLEMENTARY-II-EXPENDITURE-AND-REVENUE-ESTIMATES-FOR-FY-2024-2025.pdf"
)


def parse_pdf(file_path: str | Path | None = None) -> list[dict]:
    """
    Extract text from every page of the budget PDF.

    Returns a list of dicts: { page_number, text }
    Note: table extraction is skipped for speed on 200+ page docs.
    """
    path = Path(file_path) if file_path else DEFAULT_PDF

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(
                {
                    "page_number": i,
                    "text": text.strip(),
                }
            )
            if i % 50 == 0:
                import logging
                logging.getLogger(__name__).info(
                    "Parsed page %d/%d", i, total
                )

    return pages


def chunk_documents(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Split extracted pages into overlapping chunks suitable for embedding.

    Returns a list of dicts: { chunk_id, text, page_number, metadata }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks: list[dict] = []

    for page in pages:
        page_num = page["page_number"]
        text = page["text"]

        if not text.strip():
            continue

        page_chunks = splitter.split_text(text)
        for j, chunk_text in enumerate(page_chunks):
            chunks.append(
                {
                    "chunk_id": f"p{page_num}_c{j}",
                    "text": chunk_text,
                    "page_number": page_num,
                    "metadata": {"source_page": page_num, "chunk_index": j},
                }
            )

    return chunks
