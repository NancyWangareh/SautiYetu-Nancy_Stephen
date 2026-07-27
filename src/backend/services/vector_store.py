import time
from typing import List, Dict
from pinecone import Pinecone
from ..config import config
from .embedder import embed_text, EMBEDDING_DIM 

pc = Pinecone(api_key=config.PINECONE_API_KEY)
index = pc.Index(config.PINECONE_INDEX_NAME)

def embed_budget_line(line: Dict) -> List[float]:
    """
    Generate an embedding for a budget line description.
    Uses the pluggable embedder (local MiniLM by default).
    """
    text_to_embed = (
        f"Sector: {line.get('sector', '')}. "
        f"Sub-sector: {line.get('sub_sector', '')}. "
        f"Budget line {line.get('line_id', '')}: {line.get('description', '')}. "
        f"Amount: Ksh {line.get('amount_ksh', 0):,}. "
        f"Ward: {line.get('ward', 'county-wide')}."
    )
    return embed_text(text_to_embed)


def upload_to_pinecone(lines: List[Dict], batch_size: int = 100) -> dict:
    """
    Upload structured budget lines to Pinecone in batches.
    Each line becomes a vector with metadata for filtering.
    """
    vectors = []
    total_uploaded = 0
    failed = []

    for i, line in enumerate(lines):
        try:
            embedding = embed_budget_line(line)

            vectors.append({
                "id": f"budget-{line.get('line_id', 'unknown')}-{i}",
                "values": embedding,
                "metadata": {
                    "line_id": line.get("line_id", ""),
                    "sector": line.get("sector", ""),
                    "sub_sector": line.get("sub_sector", ""),
                    "description": line.get("description", "")[:500],
                    "amount_ksh": line.get("amount_ksh", 0),
                    "amount_requested_ksh": line.get("amount_requested_ksh", 0),
                    "ward": line.get("ward", ""),
                    "status": line.get("status", ""),
                    "fiscal_year": line.get("fiscal_year", ""),
                }
            })

            # Upload in batches
            if len(vectors) >= batch_size:
                index.upsert(vectors=vectors)
                total_uploaded += len(vectors)
                vectors = []
                time.sleep(0.5)  # Rate limit courtesy

        except Exception as e:
            failed.append({"line": line.get("line_id", f"index-{i}"), "error": str(e)})

    # Upload remaining
    if vectors:
        index.upsert(vectors=vectors)
        total_uploaded += len(vectors)
        
    print(f"✅ Upload complete: {total_uploaded} succeeded, {len(failed)} failed.")

    return {
        "total_uploaded": total_uploaded,
        "total_failed": len(failed),
        "failed_items": failed,
    }