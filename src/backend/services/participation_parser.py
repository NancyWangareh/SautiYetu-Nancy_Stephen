"""
Participation PDF Parser — extracts citizen input points from public
participation documents using pdfplumber text extraction only.

No OCR — scanned pages simply yield no text, and the human
selection step filters out garbage.
"""

import re
from pathlib import Path

import pdfplumber


# ── Splitters ─────────────────────────────────────────────────────────────

POINT_SPLITTERS = [
    re.compile(r"(?:(?<=\n)|(?<=^)|(?<=\.\s))\s*(\d{1,3})\s*[\.\)\-\–]\s+(?=[A-Z])"),
    re.compile(r"(?<=\n)\s*[•\-\*\→\✓\✔]\s+(?=\S)"),
]


def parse_participation_pdf(file_path: str | Path) -> list[dict]:
    """Extract text from each page. Skips pages with no extractable text."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page_number": i, "text": text.strip()})

    return pages


def extract_points(pages: list[dict]) -> list[dict]:
    """Break PDF pages into individual citizen input points."""
    points: list[dict] = []
    seen_texts: set[str] = set()
    counter = 0

    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]

        split_positions = _find_split_positions(page_text)
        if not split_positions:
            blocks = _fallback_split(page_text)
        else:
            blocks = []
            prev = 0
            for pos in split_positions:
                block = page_text[prev:pos].strip()
                if block:
                    blocks.append(block)
                prev = pos
            last = page_text[prev:].strip()
            if last:
                blocks.append(last)

        for block in blocks:
            cleaned = _clean_point_text(block)
            if len(cleaned) < 20:
                continue
            norm = cleaned.lower()
            if norm in seen_texts:
                continue
            seen_texts.add(norm)

            counter += 1
            points.append({
                "point_id": f"PT-{counter:03d}",
                "text": cleaned,
                "page_number": page_num,
                "section": "",
                "char_count": len(cleaned),
            })

    return points


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