import pdfplumber
from typing import List, Dict, Any
import re


def extract_raw_tables(pdf_path: str) -> dict:
    """
    Extract all tables from a digital budget PDF.
    Returns page-by-page results with metadata.
    """
    result = {
        "total_pages": 0,
        "pages_with_tables": 0,
        "total_rows_extracted": 0,
        "failed_pages": [],
        "pages": [],
    }

    with pdfplumber.open(pdf_path) as pdf:
        result["total_pages"] = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()

            if not tables:
                # Try extracting text as fallback for non-table pages
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    result["pages"].append({
                        "page_num": page_num,
                        "type": "text",
                        "content": text.strip(),
                        "rows": [],
                    })
                else:
                    result["failed_pages"].append(page_num)
                continue

            result["pages_with_tables"] += 1
            page_rows = []

            for table_idx, table in enumerate(tables):
                for row in table:
                    # Skip completely empty rows and obvious headers
                    if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                        continue

                    cleaned = [str(cell).strip() if cell else "" for cell in row]
                    
                    # Skip rows that are just headers (contain keywords like "Code", "Description")
                    if _is_header_row(cleaned):
                        continue

                    page_rows.append(cleaned)
                    result["total_rows_extracted"] += 1

            if page_rows:
                result["pages"].append({
                    "page_num": page_num,
                    "type": "table",
                    "content": None,
                    "rows": page_rows,
                })

    return result


def _is_header_row(row: List[str]) -> bool:
    """Detect if a row is a table header."""
    header_keywords = ["code", "description", "amount", "approved", "budget", 
                       "vote", "ksh", "recurrent", "development", "total"]
    row_text = " ".join(row).lower()
    return any(kw in row_text for kw in header_keywords) and len(row_text) < 120


def extract_text_fallback(pdf_path: str, failed_pages: List[int]) -> List[Dict]:
    """
    For pages where table extraction failed, extract raw text.
    These will be sent to DeepSeek Vision for processing.
    """
    fallback_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in failed_pages:
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            if text and len(text.strip()) > 20:
                fallback_pages.append({
                    "page_num": page_num,
                    "raw_text": text.strip(),
                })

    return fallback_pages