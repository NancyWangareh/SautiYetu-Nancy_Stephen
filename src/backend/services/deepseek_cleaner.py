import json
import openai
from typing import List, Dict, Any
from ..config import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

BATCH_SIZE = 30  # Send 30 rows at a time to DeepSeek


import time

def structure_budget_rows(raw_rows: List[List[str]], page_num: int) -> List[Dict]:
    """
    Send raw extracted table rows to DeepSeek and get clean, structured budget lines back.
    Processes rows in batches with rate limiting to avoid connection errors.
    """
    all_structured = []

    for batch_start in range(0, len(raw_rows), BATCH_SIZE):
        batch = raw_rows[batch_start : batch_start + BATCH_SIZE]
        
        # Retry up to 3 times with backoff
        for attempt in range(3):
            try:
                structured = _process_batch(batch, page_num)
                all_structured.extend(structured)
                break  # success — exit retry loop
            except Exception as e:
                if attempt < 2:
                    wait = (attempt + 1) * 3  # 3s, 6s
                    print(f"  Retry {attempt + 1} for page {page_num} in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  FAILED page {page_num} after 3 attempts: {e}")
        
        # Rate limit: pause between batches so DeepSeek doesn't block us
        time.sleep(0.5)

    return all_structured


def _process_batch(batch: List[List[str]], page_num: int) -> List[Dict]:
    """Process a single batch of rows through DeepSeek."""
    
    # Format rows for the prompt
    rows_text = "\n".join(
        f"Row {i}: {' | '.join(row)}" for i, row in enumerate(batch)
    )

    system_prompt = """You are a Kenyan county budget data processor. 
You receive raw rows extracted from a Nairobi City County budget PDF.

Your job: convert messy table rows into clean, structured budget line items.

Rules:
1. A "budget line" has: a code (like "42-B"), a description, and an amount in Ksh.
2. If a description spans multiple rows, MERGE them into one line item.
3. Classify each line into a sector and sub-sector based on the description.
4. If amounts appear in multiple columns, the "approved" amount is the final allocation.
5. Skip rows that are page headers, footers, totals, subtotals, or section titles.
6. If the description mentions a specific ward or location, capture it.
7. Remove footnote references like "(See Annex IV)".

Available sectors:
Health: Maternal Care, Service Delivery, NHIF
Education: Early Childhood Development, Schools & Learning, Bursaries
Infrastructure: Roads & Transport, Public Works, Housing
Water & Sanitation: Water Supply, Sewerage, Sanitation
Agriculture: Livestock Health, Crop Farming, Fisheries
Energy: Rural Electrification, Street Lighting
Security: Community Safety, Policing, Fire Services
Governance: Administration, ICT, Planning
Trade: Markets, Licensing
Environment: Waste Management, Parks, Conservation
Social Protection: Youth, Women, PWD programs
Uncategorized: anything that doesn't fit

Return ONLY a JSON array. Each object must have:
{
  "line_id": "budget code e.g. 42-B",
  "sector": "one of the sectors above",
  "sub_sector": "one of the sub-sectors above",
  "description": "clean, single-line description",
  "amount_ksh": 5000000,
  "amount_requested_ksh": 5000000,
  "ward": "ward name or null",
  "status": "matched",
  "fiscal_year": "2024/25"
}

For status: "matched" if fully funded, "partial" if partially funded, "unclear" if can't tell.
If you cannot determine the amount, set amount_ksh to null."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Process these raw budget rows from page {page_num}:\n\n{rows_text}"}
            ],
            temperature=0.0,
            max_tokens=4096,
            timeout=60,
        )

        content = response.choices[0].message.content
        
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        
        return json.loads(content)

    except json.JSONDecodeError:
        print(f"DeepSeek returned invalid JSON for page {page_num}. Raw: {content[:500]}")
        return []
    except Exception as e:
        print(f"DeepSeek error for page {page_num}: {e}")
        return []


def validate_budget_lines(lines: List[Dict]) -> dict:
    """
    Final validation pass: ask DeepSeek to check its own work.
    Catches duplicates, misclassifications, and amount errors.
    """
    if not lines:
        return {"valid": [], "issues": [], "summary": "No lines to validate"}

    system_prompt = """You are a budget data validator for Nairobi City County.

Review these structured budget lines and find issues:
1. Duplicate line_ids — flag them
2. Misclassified sectors — e.g., a "dispensary" line classified as "Education"
3. Suspicious amounts — e.g., Ksh 0 or Ksh 1 for a major project
4. Missing required fields — line_id, description, amount_ksh
5. Lines that should be merged (same project split across rows)

Return JSON:
{
  "valid_lines": [... unchanged valid lines ...],
  "issues": [
    {"line_id": "...", "field": "...", "problem": "...", "suggestion": "..."}
  ],
  "summary": "X valid lines, Y issues found"
}"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(lines, indent=2)}
            ],
            temperature=0.0,
            max_tokens=4096,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content)

    except Exception as e:
        print(f"Validation error: {e}")
        return {"valid_lines": lines, "issues": [], "summary": f"Validation skipped: {e}"}