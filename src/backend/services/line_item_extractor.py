"""
Line Item Extractor — parses Nairobi County budget PDF tables into
structured line items.

Targets the "DEVELOPMENT PROJECTS FOR THE FY ..." tables:
  S/No | Project Description | Delivery Unit | Location | Status | Approved | Supp 1 | ...
Uses pdfplumber's structured table rows (attached to each page as `tables`).
"""

import re
import logging
import uuid

logger = logging.getLogger(__name__)

# ── Section + column detection ─────────────────────────────────────────

SECTION_START = "DEVELOPMENT PROJECTS FOR THE FY"
SECTION_END_MARKERS = ("DETAILED REVENUES", "SUMMARY OF EXPENDITURE")

_AMOUNT_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$")
_CODE_RE = re.compile(r"\b(\d{8,10})\b")


def _parse_amount(val):
    """Convert '15,000,000', '0' or None to int."""
    if val is None:
        return 0
    s = str(val).replace(",", "").strip()
    try:
        return int(float(s)) if s else 0
    except (ValueError, TypeError):
        return 0


def _clean(cell):
    return re.sub(r"\s+", " ", (cell or "").strip())


def _is_amount_token(cell):
    """True if a cell is an amount ('15,000,000', '0') or empty placeholder '-'."""
    s = _clean(cell)
    if s in ("-", "\u2013", "\u2014"):
        return True
    return bool(_AMOUNT_RE.match(s))


def _find_col(header, label):
    for i, c in enumerate(header):
        if label.upper() in (c or "").upper():
            return i
    return None


def _apply_amounts(item, amts):
    if amts:
        item["approved_amount"] = _parse_amount(amts[0])
    if len(amts) > 1:
        item["revised_i_amount"] = _parse_amount(amts[1])
    if len(amts) > 2:
        item["revised_ii_amount"] = _parse_amount(amts[2])


def extract_line_items(pages, document_id, budget_type, fiscal_year):
    """
    Extract structured line items from the "DEVELOPMENT PROJECTS FOR THE FY ..."
    tables using pdfplumber's structured rows (page["tables"]).

    Reconstructs logical rows that wrap across multiple physical table rows
    (description continuation and amount continuation).
    """
    items = []
    seen = set()
    in_section = False

    for page in pages:
        text = page.get("text") or ""
        page_num = page.get("page_number", 0)

        if not in_section:
            if SECTION_START in text.upper():
                in_section = True
            else:
                continue

        if any(m in text.upper() for m in SECTION_END_MARKERS):
            break

        for table in page.get("tables") or []:
            if not table:
                continue

            header_idx = None
            for i, row in enumerate(table):
                joined = " ".join(_clean(c) for c in row).upper()
                if "S/NO" in joined and "PROJECT DESCRIPTION" in joined:
                    header_idx = i
                    break
            if header_idx is None:
                continue

            header = table[header_idx]
            sno_c = _find_col(header, "S/No")
            desc_c = _find_col(header, "Project Description")
            delivery_c = _find_col(header, "Delivery Unit")
            location_c = _find_col(header, "Location")
            if sno_c is None or desc_c is None:
                continue

            current = None

            def flush():
                nonlocal current
                if current and current.get("description"):
                    key = (
                        current["description"][:60].lower(),
                        current.get("project_code"),
                        current.get("location"),
                    )
                    if key not in seen:
                        seen.add(key)
                        current["document_id"] = document_id
                        current["budget_type"] = budget_type
                        current["fiscal_year"] = fiscal_year
                        current["page_number"] = page_num
                        items.append(current)
                current = None

            for row in table[header_idx + 1:]:
                sno = _clean(row[sno_c]) if sno_c < len(row) else ""
                desc = _clean(row[desc_c]) if desc_c < len(row) else ""
                delivery = _clean(row[delivery_c]) if delivery_c is not None and delivery_c < len(row) else ""
                location = _clean(row[location_c]) if location_c is not None and location_c < len(row) else ""
                amts = [c for i, c in enumerate(row) if i != sno_c and _is_amount_token(c)]

                if sno.isdigit():
                    flush()
                    if not desc:
                        # subtotal row (department name sits in another column)
                        continue

                    code = None
                    m = _CODE_RE.search(delivery)
                    if m:
                        code = m.group(1)
                        delivery = _CODE_RE.sub("", delivery).strip()

                    current = {
                        "s_no": int(sno),
                        "project_code": code,
                        "project_name": desc[:300],
                        "description": desc[:500],
                        "delivery_unit": delivery[:200] or None,
                        "location": location[:200] or None,
                        "approved_amount": 0,
                        "revised_i_amount": 0,
                        "revised_ii_amount": 0,
                        "source_text": " ".join(_clean(c) for c in row)[:1000],
                    }
                    _apply_amounts(current, amts)
                else:
                    if current is None:
                        continue
                    if desc:
                        current["description"] = (current["description"] + " " + desc).strip()[:500]
                        current["project_name"] = current["description"][:300]
                    if amts and not current["approved_amount"]:
                        _apply_amounts(current, amts)

            flush()

    logger.info(
        "Extracted %d line items from %d pages (doc=%s, type=%s)",
        len(items), len(pages), document_id, budget_type,
    )
    return items

def build_search_text(item: dict) -> str:
    """Search text for a line item: description only (location stays in the payload)."""
    return item.get("description") or item.get("project_name") or ""


def line_items_to_chunks(items: list[dict]) -> list[dict]:
    """Turn structured line items into Qdrant chunks with enriched payload."""
    chunks = []
    for it in items:
        text = build_search_text(it).strip()
        if len(text) < 5:
            continue
        chunks.append({
            "chunk_id": f"LI-{it.get('project_code') or it.get('s_no') or uuid.uuid4().hex[:8]}",
            "text": text,
            "page_number": it.get("page_number"),
            "location": it.get("location"),
            "ward": it.get("ward"),
            "subcounty": it.get("subcounty"),
            "sector": it.get("sector"),
            "sub_sector": it.get("sub_sector"),
            "amount_ksh": it.get("approved_amount"),
            "project_code": it.get("project_code"),
        })
    return chunks