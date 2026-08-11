"""
Line Item Extractor — parses Nairobi County budget PDF tables into
structured line items with project codes, descriptions, and amounts.

Handles the specific table format used in NCCG budget documents:
  S/No | Project Description | Code | Delivery Unit | Location | 
  Approved | Revised I | Revised II
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Patterns for NCCG budget table rows ────────────────────────────────

# Pattern: number followed by project code (like 5332000900) then description
# Captures: s_no, code, description, location, approved, revised_i, revised_ii
LINE_ITEM_PATTERN = re.compile(
    r"(\d{1,3})\s+"                              # S/No
    r"(\d{8,10})\s+"                              # Project code (8-10 digits)
    r"(.+?)\s+"                                   # Description (greedy)
    r"([A-Z][a-zA-Z\s\-']+?)\s+"                  # Location (capitalized word)
    r"([\d,]+)\s+"                                # Approved amount
    r"([\d,]+)\s+"                                # Revised I
    r"([\d,]+)"                                   # Revised II
)

# Simpler pattern for rows without location
LINE_ITEM_SIMPLE = re.compile(
    r"(\d{1,3})\s+"                               # S/No  
    r"(\d{8,10})\s+"                              # Project code
    r"(.+?)\s+"                                   # Description
    r"([\d,]+)\s+"                                # Amount 1
    r"([\d,]+)\s+"                                # Amount 2
    r"([\d,]+)"                                   # Amount 3
)

# Detect a budget table row (has project code + amounts)
TABLE_ROW_DETECT = re.compile(r"\d{8,10}.*?[\d,]{4,}\s+[\d,]{4,}")


def _parse_amount(val: str) -> int:
    """Convert '15,000,000' or '0' to int."""
    try:
        return int(val.replace(",", ""))
    except (ValueError, AttributeError):
        return 0


def extract_line_items(pages: list[dict], document_id: str, budget_type: str, fiscal_year: str) -> list[dict]:
    """
    Scan all pages for budget table rows and extract structured line items.

    Returns list of dicts ready for BudgetLineItem insertion.
    """
    items = []
    seen_texts = set()

    for page in pages:
        page_num = page["page_number"]
        text = page["text"]

        for line in text.split("\n"):
            line = line.strip()
            if len(line) < 40:
                continue

            # Must look like a budget table row
            if not TABLE_ROW_DETECT.search(line):
                continue

            # Dedup
            norm = re.sub(r"\s+", " ", line)[:100].lower()
            if norm in seen_texts:
                continue
            seen_texts.add(norm)

            # Try full pattern first
            match = LINE_ITEM_PATTERN.search(line)
            if match:
                items.append({
                    "document_id": document_id,
                    "budget_type": budget_type,
                    "fiscal_year": fiscal_year,
                    "page_number": page_num,
                    "s_no": int(match.group(1)),
                    "project_code": match.group(2),
                    "description": match.group(3).strip()[:500],
                    "location": match.group(4).strip()[:200],
                    "approved_amount": _parse_amount(match.group(5)),
                    "revised_i_amount": _parse_amount(match.group(6)),
                    "revised_ii_amount": _parse_amount(match.group(7)),
                    "source_text": line[:1000],
                    "project_name": match.group(3).strip()[:300],
                })
                continue

            # Try simpler pattern
            match = LINE_ITEM_SIMPLE.search(line)
            if match:
                items.append({
                    "document_id": document_id,
                    "budget_type": budget_type,
                    "fiscal_year": fiscal_year,
                    "page_number": page_num,
                    "s_no": int(match.group(1)),
                    "project_code": match.group(2),
                    "description": match.group(3).strip()[:500],
                    "location": None,
                    "approved_amount": _parse_amount(match.group(4)),
                    "revised_i_amount": _parse_amount(match.group(5)),
                    "revised_ii_amount": _parse_amount(match.group(6)),
                    "source_text": line[:1000],
                    "project_name": match.group(3).strip()[:300],
                })

    logger.info(
        "Extracted %d line items from %d pages (doc=%s, type=%s)",
        len(items), len(pages), document_id, budget_type,
    )
    return items