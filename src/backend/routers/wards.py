from fastapi import APIRouter
from pathlib import Path
import csv

router = APIRouter(prefix="/api", tags=["wards"])

WARDS_PATH = Path(__file__).resolve().parents[3] / "Data" / "wards.csv"


@router.get("/wards")
def get_wards():
    if not WARDS_PATH.exists():
        return [
            {"ward_name": "Umoja I", "constituency": "Embakasi East"},
            {"ward_name": "Umoja II", "constituency": "Embakasi East"},
        ]
    with open(WARDS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))