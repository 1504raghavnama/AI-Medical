# AI Medical Coding System

AI-powered ICD-10-CM and HCPCS code suggestion from clinical notes.

## Architecture
- **Layer 1** — Input: Clinical notes via REST API
- **Layer 2** — NLP: Phrase extraction + negation detection
- **Layer 3** — Coding Engine: Word2Vec RAG + reranking
- **Layer 4** — Knowledge Base: ICD-10-CM 2026 (74,719 codes) + HCPCS (1,689 codes)
- **Layer 5** — Output: Structured JSON with confidence scores
- **Layer 6** — Human Review: Accept/Reject UI with feedback storage
- **Layer 7** — Integration: FastAPI REST endpoints
- **Layer 8** — Governance: SQLite audit logging
- **Layer 9** — Infrastructure: Docker containerization

## Tech Stack
- Python 3.11
- FastAPI + Uvicorn
- BiLSTM-CRF (NER)
- Word2Vec (Medical embeddings)
- ChromaDB (Vector DB)
- HTML/CSS/JS (Frontend)
- Docker

## Setup

### Local
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Docker
```bash
docker build -t ai-medical .
docker run -p 8000:8000 ai-medical
```

## API Endpoints
- `GET /health` — system status
- `POST /analyze` — accepts clinical note, returns ICD-10 codes
- `POST /feedback` — stores coder accept/reject decisions

## Author
Raghav Nama | Internship Project | June 2026