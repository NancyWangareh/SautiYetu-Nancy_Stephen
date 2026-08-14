"""
Participation PDF Parser — extracts citizen input points from public
participation documents using pdfplumber text extraction, with an OCR
fallback for scanned PDFs.

The human selection step filters out garbage.
"""

import io
import re
from pathlib import Path

import pdfplumber
from .geo import SUBCOUNTIES


# ── Splitters ─────────────────────────────────────────────────────────────

POINT_SPLITTERS = [
    re.compile(r"(?:(?<=\n)|(?<=^)|(?<=\.\s))\s*(\d{1,3})\s*[\.\)\-\–]\s+(?=[A-Z])"),
    re.compile(r"(?<=\n)\s*[•\-\*\→\✓\✔]\s+(?=\S)"),
]

def _extract_text_pages(path: Path) -> list[dict]:
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page_number": i, "text": text.strip()})
    return pages


def _ocr_pages(path: Path) -> list[dict]:
    """Fallback for scanned PDFs: render pages to images and OCR them."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            "This PDF is scanned (no text layer). Install OCR support: "
            "pip install pymupdf pytesseract pillow, and install Tesseract OCR."
        ) from e

    pages = []
    with fitz.open(str(path)) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
            if text.strip():
                pages.append({"page_number": i, "text": text.strip()})
    return pages


def parse_participation_pdf(file_path: str | Path) -> list[dict]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = _extract_text_pages(path)
    if not pages: 
        pages = _ocr_pages(path)
    return pages


def _looks_like_section_header(line: str) -> str | None:
    s = re.sub(r"\s+", " ", line).strip()
    if not s or len(s) < 3 or len(s) > 80:
        return None
    for sc in SUBCOUNTIES:
        if sc.lower() in s.lower():
            return sc
    if s.isupper() and len(s.split()) <= 6 and not re.search(r"\d", s):
        return s.title()
    return None


def extract_points(pages: list[dict]) -> list[dict]:
    """Break PDF pages into citizen points, tracking the current subcounty section."""
    points: list[dict] = []
    seen_texts: set[str] = set()
    counter = 0

    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]
        current_section = ""

        # Prefer numbered/bullet/blank-line splits; fall back to sentences
        positions = _find_split_positions(page_text)
        blocks = (
            _split_by_positions(page_text, positions)
            if positions
            else _fallback_split(page_text)
        )

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # If the block starts with a subcounty header, update the section
            first_line = block.split("\n", 1)[0].strip()
            header = _looks_like_section_header(first_line)
            if header:
                current_section = header
                block = block[len(first_line):].strip()
                if not block:
                    continue

            cleaned = _clean_point_text(block)
            if len(cleaned) < 20:
                continue
            if cleaned.lower() in seen_texts:
                continue
            seen_texts.add(cleaned.lower())
            counter += 1
            points.append({
                "point_id": f"PT-{counter:03d}",
                "text": cleaned,
                "page_number": page_num,
                "section": current_section,
                "char_count": len(cleaned),
            })

    return points


def _split_by_positions(text: str, positions: list[int]) -> list[str]:
    blocks: list[str] = []
    prev = 0
    for pos in positions:
        block = text[prev:pos].strip()
        if block:
            blocks.append(block)
        prev = pos
    last = text[prev:].strip()
    if last:
        blocks.append(last)
    return blocks

def _find_split_positions(text: str) -> list[int]:
    positions: set[int] = set()
    for pattern in POINT_SPLITTERS:
        for m in pattern.finditer(text):
            positions.add(m.start())
    for m in re.finditer(r"\n\s*\n", text):
        positions.add(m.start())
    positions.discard(0)
    return sorted(positions)


def _clean_point_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\s•\-\*\→\✓\✔\d\.\)\:]+", "", text)
    return text.strip()


def _fallback_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    merged = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) < 30 and merged:
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)
    return merged


def process_participation_pdf(file_path: str, county: str | None = None) -> dict:
    """Full pipeline: parse PDF → extract points."""
    pages = parse_participation_pdf(file_path)
    filename = Path(file_path).name
    points = extract_points(pages)

    return {
        "filename": filename,
        "pages_parsed": len(pages),
        "points_extracted": len(points),
        "county": county or "all",
        "points": points,
    }