# SautiYetu

> Built during the **Democracy & AI Hackathon** — July 4th, 2026  
> Hosted by **Mozilla Foundation** & **KamiLimu**

---

## Team

| Name | Role | GitHub |
|---|---|---|
| Nancy Wangare | Data Engineer | [@nancywangare](https://github.com/NancyWangareh) |
| Stephen Chacha | Software Engineer | [@stephenchacha](https://github.com/estebanchurchur) |

**Team Name:** SautiYetu &nbsp;|&nbsp; **University:** [Chuka University & Nairobi University]

---

## Problem & User

### Problem Statement

> Kenyan civil society organizations (CSOs) involved in county budget processes face a profound deficit of accountability, where public input disappears without trace or verifiable impact. This systemic failure is evidenced by the International Budget Partnership's County Budget Transparency Survey 2024, which highlights that local governments consistently fail to provide official feedback on public participation. Despite existing transparency platforms like Open County, which successfully visualize top-down government spending, there remains a critical gap: these tools lack a bottom-up data pipeline to track public feedback against enacted budget lines.

### Target User

| Dimension | Detail |
|---|---|
| **Primary user** | A CSO budget watchdog or community-based organization in Nairobi County monitoring whether citizen proposals are reflected in enacted budgets |
| **Tech comfort** | Comfortable with web dashboards and spreadsheets |
| **Language** | Swahili, English (Interchangeable) |
| **Current workflow** | Manually compares town hall notes against dense 300+ page county budget PDFs — slow, error-prone, and impossible to scale |

### The Specific Gap

1. **What's already there:** Open County platform (Open Institute / World Bank) digitizes county budgets into visual dashboards; County Budget Transparency Survey publishes annual audit reports.
2. **Why it falls short:** These are top-down tools — they show what the government *says* it spent, but provide no pipeline for ingesting, tracking, or measuring what citizens *actually requested*.
3. **The gap we fill:** A bottom-up ingestion and matching pipeline that uses AI (sentence-transformer embeddings + an LLM) to auto-categorize unstructured citizen input by sector and location, then cross-references it against enacted budget line items — producing a visible, contestable verdict for every request: **Present** (funded) or **Absent** (not funded).

### Why It Matters

> When CSOs cannot track whether citizen priorities made it into the final budget, public participation becomes a compliance ritual rather than a democratic mechanism. The Open Budget Survey 2023 scores Kenya's public participation at 31/100 — and a shocking 0/100 for post-approval participation during budget implementation and audit. Closing this feedback loop restores the basic accountability contract: citizens speak, government responds, and watchdogs can verify.


## Run Instructions

### Prerequisites

- **Python** 3.10+ (backend)
- **Node.js** 18+ and **npm** 9+ (frontend)
- A **DeepSeek API key** (for classification, verification and simplification)

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/NancyWangareh/SautiYetu-Nancy_Stephen
cd SautiYetu-Nancy_Stephen

# 2. Backend
cd src/backend
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../../deploy/env.backend .env   # then set DEEPSEEK_API_KEY
uvicorn backend.main:app --reload  # http://localhost:8000

# 3. Frontend (new terminal)
cd ../frontend
npm install
npm run dev

# 4. Open http://localhost:5173 in your browser
```

### Project Structure
```bash
.
├── README.md
├── LICENSE
├── Data/
│   └── wards.csv                  ← Nairobi wards reference data
├── deploy/                        ← nginx, systemd, env template, VPS guide
└── src/
    ├── backend/
    │   ├── main.py                ← FastAPI app + routers
    │   ├── db/                    ← SQLAlchemy models + async database
    │   ├── routers/               ← budget, participation, matches, reports
    │   ├── schemas/               ← Pydantic request/response models
    │   └── services/
    │       ├── classifier.py      ← LLM sector/sub-sector classification
    │       ├── embedder.py        ← sentence-transformer embeddings
    │       ├── ingestion.py       ← PDF parsing & chunking
    │       ├── matcher.py         ← semantic matching + LLM verification
    │       ├── participation_matcher.py  ← citizen point ↔ budget matching
    │       ├── vector_store.py    ← Qdrant wrapper
    │       ├── line_item_extractor.py    ← budget PDF table parsing
    │       ├── participation_parser.py   ← participation PDF parsing (OCR)
    │       ├── simplifier.py      ← plain-language explanations
    │       └── geo.py             ← ward → sub-county normalisation
    └── frontend/
        ├── index.html
        ├── vite.config.js
        └── src/
            ├── App.jsx            ← sidebar navigation + routing
            ├── pages/             ← Landing, BudgetUpload, Participation,
            │                        Matches, Reports, Submissions,
            │                        BudgetDocuments, Input
            └── data/              ← API client + reactive store
```

### Approach & Architecture

```text
Enacted budget PDF ──▶ parse & extract line items ──▶ embed (e5-small) ──▶ Qdrant
Citizen concern ──▶ classify (LLM) ──▶ location-aware match ──▶ Present / Absent
                                                           └─▶ plain-language explanation
```

| Layer | Tech |
|---|---|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | FastAPI (Python 3.12, async) |
| Vector store | Qdrant (local embedded) |
| Database | SQLite (SQLAlchemy async) |
| Embeddings | `intfloat/multilingual-e5-small` |
| LLM | DeepSeek (classification, verification, simplification) |

---

## Built vs Mocked

| Component | Status | Notes |
|---|---|---|
| Budget PDF upload & ingestion | ✅ Built | Parses the enacted budget PDF into structured line items |
| Structured line-item extraction | ✅ Built | Table-aware parsing of the DEVELOPMENT PROJECTS section |
| Participation PDF upload | ✅ Built | Extracts citizen concerns, OCR fallback for scanned PDFs |
| AI classification | ✅ Built | DeepSeek LLM classifies concerns & budget lines by sector/sub-sector |
| Semantic search | ✅ Built | `multilingual-e5-small` embeddings + Qdrant |
| Location-aware matching | ✅ Built | Ward/sub-county normalisation + filtered search + LLM verification |
| Present / Absent verdicts | ✅ Built | Two-state outcome per citizen concern |
| Plain-language explanations | ✅ Built | LLM simplification with rule-based fallback |
| CSO Reports | ✅ Built | Funding-gap analysis by sector/ward, CSV export |
| Landing page | ✅ Built | Public landing page leading to the dashboard |
| Swahili understanding | ✅ Built | Multilingual embedding model (English + Swahili) |

## License
MIT © SautiYetu, 2026