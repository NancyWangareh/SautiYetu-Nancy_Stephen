"""Location normalization — maps wards/estates to a canonical ward + subcounty."""

import csv
import re
from pathlib import Path

# Nairobi's 17 subcounties (former constituencies)
SUBCOUNTIES = [
    "Westlands", "Dagoretti North", "Dagoretti South", "Langata", "Kibra",
    "Roysambu", "Kasarani", "Ruaraka", "Embakasi South", "Embakasi North",
    "Embakasi Central", "Embakasi East", "Embakasi West", "Makadara",
    "Kamukunji", "Starehe", "Mathare",
]

# Starter aliases — EXPAND THIS from authoritative data (estates → subcounty)
SUBCOUNTY_ALIASES = {
    "lang'ata": "Langata",
    "langata": "Langata",
    "kangemi": "Westlands",
    "kibera": "Kibra",
}

_ward_to_subcounty: dict[str, str] = {}
_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return

    # Primary source: Data/wards.csv with columns: ward_name, subcounty
    path = Path(__file__).resolve().parents[3] / "Data" / "wards.csv"
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ward = (row.get("ward_name") or "").strip().lower()
                sc = (row.get("subcounty") or "").strip()
                if ward and sc:
                    _ward_to_subcounty[ward] = sc

    # Subcounty names normalize to themselves
    for sc in SUBCOUNTIES:
        _ward_to_subcounty.setdefault(sc.lower(), sc)

    _loaded = True


def normalize_location(raw: str | None) -> dict | None:
    """Return {"ward": ..., "subcounty": ...} for a citizen/budget location string."""
    if not raw:
        return None
    _load()

    text = re.sub(r"[^\w\s'\-]", " ", raw.lower()).strip()

    if text in _ward_to_subcounty:
        return {"ward": raw.strip(), "subcounty": _ward_to_subcounty[text]}

    # longest known name appearing as a substring (e.g. "Mathare VTC" → Mathare)
    best = None
    for name, sc in _ward_to_subcounty.items():
        if name in text and (best is None or len(name) > len(best[0])):
            best = (name, sc)
    if best:
        return {"ward": raw.strip(), "subcounty": best[1]}

    for alias, sc in SUBCOUNTY_ALIASES.items():
        if alias in text:
            return {"ward": raw.strip(), "subcounty": sc}

    return None