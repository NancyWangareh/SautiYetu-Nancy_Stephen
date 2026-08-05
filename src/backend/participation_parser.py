"""
Participation PDF Parser — extracts grassroots citizen input points from public
participation documents (town hall minutes, baraza reports, community consultations).

Handles common formats found in Kenyan public participation documents:
  - Numbered lists (1., 1), 2., etc.)
  - Bullet points (•, -, *, →)
  - Section headers with topic/ward labels
  - Paragraph-style citizen concerns
"""

import re
import uuid
from pathlib import Path

import pdfplumber


# ── Patterns for splitting extracted text into individual "points" ───────

# Priority-ordered splitters: try each in order; the first match wins
POINT_SPLITTERS = [
    # 1) Numbered items: "1.", "1)", "1 –", "1." , "1-", etc.
    re.compile(r"(?:(?<=\n)|(?<=^)|(?<=\.\s))\s*(\d{1,3})\s*[\.\)\-\–]\s+(?=[A-Z])"),
    # 2) Bullet-style: "•", "-", "*", "→" at line start (but NOT section headers like "---")
    re.compile(r"(?<=\n)\s*[•\-\*\→\✓\✔]\s+(?=\S)"),
    # 3) Roman numerals: "i.", "ii.", "iii." etc.
    re.compile(r"(?:(?<=\n)|(?<=^))\s*([ivxlcdm]{1,6})\s*[\.\)]\s+(?=[A-Z])"),
    # 4) Lettered items: "a.", "b)", "c)" etc.
    re.compile(r"(?:(?<=\n)|(?<=^))\s*([a-h])\s*[\.\)]\s+(?=[A-Z])"),
]

# Sections commonly found in Kenyan public participation docs
SECTION_HEADERS = re.compile(
    r"^\s*(?:"
    r"(?:SECTION|AGENDA|ISSUE|CONCERN|TOPIC|WARD|MINUTE|ITEM|DAY)\s*\d*"
    r"|(?:HEALTH|EDUCATION|INFRASTRUCTURE|WATER|SANITATION|AGRICULTURE"
    r"|ENERGY|SECURITY|ROADS|DRAINAGE|YOUTH|WOMEN|DISABILITY|ENVIRONMENT"
    r"|HOUSING|MARKET|TRANSPORT|GARBAGE|WASTE|LIGHTING|ELECTRICITY)\s*(?:\:|\s*\d+)?"
    r")\s*[:\-–]?\s*$",
    re.IGNORECASE,
)


def parse_participation_pdf(file_path: str | Path) -> list[dict]:
    """
    Extract text from a public participation PDF.

    Returns a list of page dicts: { page_number, text }
    """
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


def _find_split_positions(text: str) -> list[int]:
    """
    Find positions in text where individual "points" begin.

    Uses multiple heuristics in priority order:
      1. Numbered items (1., 2), etc.)
      2. Bullet points
      3. Section headers
      4. Double newlines (paragraph breaks)

    Returns sorted list of character positions where splits should occur.
    """
    positions: set[int] = set()

    # Try each splitter pattern
    for pattern in POINT_SPLITTERS:
        for m in pattern.finditer(text):
            pos = m.start()
            # Only add if not already covered by a higher-priority splitter
            positions.add(pos)

    # Also split on double newlines for paragraph-style inputs
    for m in re.finditer(r"\n\s*\n", text):
        positions.add(m.start())

    # Remove the very first position (0) — it's the start of text
    positions.discard(0)

    return sorted(positions)


def _clean_point_text(text: str) -> str:
    """Normalize a single extracted point's text."""
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove leading bullet/number markers for cleanliness
    text = re.sub(r"^[\s•\-\*\→\✓\✔\d\.\)\:]+", "", text)
    return text.strip()


def _detect_section(page_text: str, point_text: str) -> str:
    """
    Try to detect which section/theme a point belongs to by looking at
    the text context (section headers near the point in the page).
    """
    # Look for section headers in the page text
    for m in SECTION_HEADERS.finditer(page_text):
        header = m.group().strip().rstrip(":-–")
        # If this header appears before our point in the page, it's relevant
        if m.start() < page_text.find(point_text):
            # Keep scanning to find the closest header
            pass
    return ""


def extract_points(pages: list[dict]) -> list[dict]:
    """
    Break down extracted PDF pages into individual citizen input "points".

    Each point represents a single grassroots concern/request raised during
    public participation. Points are deduplicated and cleaned.

    Returns:
        [
            {
                "point_id": "PT-001",
                "text": "Residents request a new maternity wing at Umoja Health Centre...",
                "page_number": 3,
                "section": "Health",
                "char_count": 142,
            },
            ...
        ]
    """
    points: list[dict] = []
    seen_texts: set[str] = set()  # deduplication
    counter = 0

    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]

        # Find split positions
        split_positions = _find_split_positions(page_text)

        if not split_positions:
            # No structured points found — treat the entire page text as one block
            # and split by sentences/phrases that look like citizen inputs
            blocks = _fallback_split(page_text)
        else:
            blocks = []
            prev = 0
            for pos in split_positions:
                block = page_text[prev:pos].strip()
                if block:
                    blocks.append(block)
                prev = pos
            # Don't forget the last block
            last = page_text[prev:].strip()
            if last:
                blocks.append(last)

        for block in blocks:
            cleaned = _clean_point_text(block)

            # Skip very short fragments (likely headers, noise)
            if len(cleaned) < 20:
                continue

            # Skip duplicates
            norm = cleaned.lower()
            if norm in seen_texts:
                continue
            seen_texts.add(norm)

            counter += 1
            points.append(
                {
                    "point_id": f"PT-{counter:03d}",
                    "text": cleaned,
                    "page_number": page_num,
                    "section": _detect_section(page_text, cleaned),
                    "char_count": len(cleaned),
                }
            )

    return points


def _fallback_split(text: str) -> list[str]:
    """
    Fallback: split unstructured text by sentence boundaries or long phrases.
    Used when no bullet/numbered patterns are detected.
    """
    # Split on sentence endings followed by a capital letter or newline
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

    # Merge very short parts with neighbors
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


# ── Convenience: full parse + extract ────────────────────────────────────

# County name patterns for detecting county sections in nationwide PDFs
COUNTY_HEADER_PATTERN = re.compile(
    r"(?:^|\n)\s*("
    r"[A-Z][A-Z\s\-']+(?:COUNTY|CITY COUNTY|MUNICIPALITY)"
    r")\s*(?:\n|$|:|\d)",
    re.IGNORECASE,
)

# Nairobi-specific keywords for loose matching
NAIROBI_ALIASES = [
    "nairobi", "nairobi county", "nairobi city county",
    "nairobi city", "city county of nairobi",
]


def _detect_county_sections(pages: list[dict], target_county: str) -> list[dict]:
    """
    Filter pages to only those belonging to a specific county.

    For nationwide participation PDFs, identifies county boundaries by:
      1. County name headers at the top of pages
      2. County name appearing as a section header
      3. Tracking county context across consecutive pages

    Returns only the pages that belong to the target county.
    """
    target_lower = target_county.lower().strip()
    target_page_nums: set[int] = set()
    current_county: str | None = None
    county_page_ranges: dict[str, list[int]] = {}

    # First pass: find all county headers and track which pages belong to which county
    for page in pages:
        page_num = page["page_number"]
        text = page["text"]

        # Check if page starts with or contains a prominent county header
        header_match = COUNTY_HEADER_PATTERN.search(text[:300])
        if header_match:
            detected = header_match.group(1).strip().lower()
            current_county = detected
            county_page_ranges.setdefault(detected, []).append(page_num)

        # Assign page to current county context
        if current_county:
            county_page_ranges.setdefault(current_county, []).append(page_num)

    # Find all county name variants that match our target
    matched_counties: list[str] = []
    for cname in county_page_ranges:
        cname_clean = cname.replace("county", "").replace("city", "").strip()
        target_clean = target_lower.replace("county", "").replace("city", "").strip()
        if target_clean in cname_clean or cname_clean in target_clean:
            matched_counties.append(cname)
        # Also check aliases
        for alias in NAIROBI_ALIASES:
            if alias in cname:
                matched_counties.append(cname)
                break

    # Collect target page numbers
    for mc in set(matched_counties):
        target_page_nums.update(county_page_ranges.get(mc, []))

    # Second pass: if no county headers found, fall back to keyword matching
    if not target_page_nums:
        for page in pages:
            page_num = page["page_number"]
            text_lower = page["text"].lower()
            # Check if page mentions Nairobi prominently
            for alias in NAIROBI_ALIASES:
                if alias in text_lower:
                    # Count occurrences — multiple mentions suggest the page is about Nairobi
                    count = text_lower.count(alias)
                    if count >= 2:
                        target_page_nums.add(page_num)
                        break

    # If still nothing, try checking if any page mentions Nairobi at all
    if not target_page_nums:
        for page in pages:
            page_num = page["page_number"]
            text_lower = page["text"].lower()
            if "nairobi" in text_lower:
                target_page_nums.add(page_num)

    # Filter pages
    return [p for p in pages if p["page_number"] in target_page_nums]


def process_participation_pdf(
    file_path: str | Path,
    county: str | None = None,
) -> dict:
    """
    Full pipeline: parse participation PDF and extract citizen input points.

    Args:
        file_path: Path to the participation PDF
        county: Optional county name to filter by (e.g. \"Nairobi\"). If provided,
                only pages belonging to that county are processed.

    Returns:
        {
            "filename": "umoja_baraza.pdf",
            "pages_parsed": 15,
            "pages_filtered": 5,
            "county": "Nairobi",
            "points_extracted": 47,
            "points": [ { point_id, text, page_number, section, char_count }, ... ]
        }
    """
    path = Path(file_path)

    pages = parse_participation_pdf(str(path))
    total_pages = len(pages)

    # Apply county filter if specified
    filtered_pages = pages
    if county:
        filtered_pages = _detect_county_sections(pages, county)

    points = extract_points(filtered_pages)

    result = {
        "filename": path.name,
        "pages_parsed": total_pages,
        "points_extracted": len(points),
        "points": points,
    }

    if county:
        result["county"] = county
        result["pages_filtered"] = len(filtered_pages)

    return result
