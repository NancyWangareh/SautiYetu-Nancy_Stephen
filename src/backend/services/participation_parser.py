"""
Participation PDF Parser — extracts grassroots citizen input points from public
participation documents (town hall minutes, baraza reports).
"""

import re
import uuid
from pathlib import Path

import pdfplumber


# ── Splitters ─────────────────────────────────────────────────────────────

POINT_SPLITTERS = [
    re.compile(r"(?:(?<=\n)|(?<=^)|(?<=\.\s))\s*(\d{1,3})\s*[\.\)\-\–]\s+(?=[A-Z])"),
    re.compile(r"(?<=\n)\s*[•\-\*\→\✓\✔]\s+(?=\S)"),
]

SECTION_HEADERS = re.compile(
    r"^\s*(?:SECTION|AGENDA|ISSUE|CONCERN|TOPIC|WARD|MINUTE|ITEM"
    r"|HEALTH|EDUCATION|INFRASTRUCTURE|WATER|SANITATION|AGRICULTURE"
    r"|ENERGY|SECURITY|ROADS|DRAINAGE|YOUTH|WOMEN|DISABILITY|ENVIRONMENT"
    r"|HOUSING|MARKET|TRANSPORT|GARBAGE|WASTE|LIGHTING|ELECTRICITY)\s*[:\-]?\s*$",
    re.IGNORECASE,
)

COUNTY_HEADER_PATTERN = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Z\s\-']+(?:COUNTY|CITY COUNTY|MUNICIPALITY))\s*(?:\n|$|:|\d)",
    re.IGNORECASE,
)


def parse_participation_pdf(file_path: str | Path) -> list[dict]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            if len(text.strip()) < 50 or _is_garbled(text):
                ocr_text = _ocr_page(page, i)
                if ocr_text.strip():
                    text = ocr_text
                # If OCR also failed, still include the page with whatever we got
                # Don't skip — return empty text so extract_points can still try

            pages.append({"page_number": i, "text": text.strip() if text.strip() else ""})

    return pages


def _is_garbled(text: str) -> bool:
    """Detect if extracted text is likely scanned-garbage rather than real text."""
    stripped = text.strip()
    if len(stripped) < 30:
        return True
    # Count ratio of alphabetic characters
    alpha = sum(1 for c in stripped if c.isalpha() or c.isspace() or c.isdigit())
    # Garbled text has lots of symbols like "I I ri;:i I l 'i-i-i"
    if alpha < len(stripped) * 0.5:   # was 0.3, now stricter
        return True
    # If text contains actual English words, it's probably real
    common_words = ["the", "and", "for", "county", "budget", "public", "road", "school", "health"]
    word_count = sum(1 for w in common_words if w in stripped.lower())
    if word_count >= 2:
        return False  # definitely real text
    return False  # default: trust pdfplumber


def _ocr_page(page, page_num: int) -> str:
    """OCR a page using Tesseract."""
    try:
        import pytesseract
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Users\bagic\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        )

        img = page.to_image(resolution=300)
        pil_image = img.original.convert("L")
        text = pytesseract.image_to_string(pil_image, lang="eng")
        return text
    except ImportError:
        return ""
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("OCR skipped page %d: %s", page_num, e)
        return ""
    
def extract_points(pages: list[dict]) -> list[dict]:
    """Break PDF pages into individual citizen input 'points'."""
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
    """
    Full pipeline: parse PDF → extract points → optionally filter by county.
    Returns a dict with stats and extracted points.
    """
    pages = parse_participation_pdf(file_path)
    filename = Path(file_path).name

    # Filter by county if specified
    if county:
        filtered = _filter_by_county(pages, county)
        if filtered:
            pages = filtered

    points = extract_points(pages)

    return {
        "filename": filename,
        "pages_parsed": len(pages),
        "points_extracted": len(points),
        "county": county or "all",
        "points": points,
    }


def _filter_by_county(pages: list[dict], target_county: str) -> list[dict]:
    """Filter pages to only those belonging to a specific county."""
    target_lower = target_county.lower().strip()
    filtered = []
    current_county = None

    for page in pages:
        text = page["text"]
        match = COUNTY_HEADER_PATTERN.search(text[:500])
        if match:
            current_county = match.group(1).strip().lower()
        if current_county is None or target_lower in current_county:
            filtered.append(page)

    return filtered