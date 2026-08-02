# Investment Research Assistant — Project Summary

An end-to-end overview of the project: what it is, what has been built, what is still
missing, and what is required to run and deploy it.

---

## 1. What This Project Is

An **AI-powered Investment Research Assistant** that answers financial questions about
semiconductor companies (NVIDIA, AMD, Intel). Given a natural-language query, it:

1. Classifies the query to decide which data sources ("tools") are needed.
2. Extracts the target company/ticker.
3. Gathers **live market data**, **latest news**, and **document insights (RAG)**.
4. Feeds the combined context into **Google Gemini 2.5 Flash Lite** to synthesize a
   structured, factual answer.

The project exists in **two parallel implementations**:

| Implementation | Location | Purpose | Status |
|----------------|----------|---------|--------|
| **Serverless (AWS SAM)** | `lambdas/`, `template.yaml` | Production cloud deployment | Primary / active |
| **Local (FastAPI)** | `src/` | Local dev, RAG experimentation | Secondary / partial |

---

## 2. Architecture

### Serverless (AWS SAM) — the primary path

```
Client ──POST /ask──► API Gateway ──► AgentLambda (orchestrator)
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
             MarketDataLambda        NewsLambda          RetrieverLambda
              (yfinance)            (feedparser RSS)      (FAISS + S3)
                    │                     │                     │
                    └─────────────────────┴─────────────────────┘
                                          ▼
                                  Gemini 2.5 Flash Lite
                                          ▼
                              Structured JSON answer
```

- **AgentLambda** — orchestrator. Classifies query, extracts company, invokes child
  lambdas via `boto3`, builds context, calls Gemini. Exposes `POST /ask`.
- **MarketDataLambda** — real-time price/open/high/low/volume/market cap/P-E via `yfinance`.
- **NewsLambda** — latest headlines via Yahoo Finance RSS (`feedparser`).
- **RetrieverLambda** — RAG over financial PDFs; FAISS vector search, index + metadata
  pulled from S3 bucket `investment-research-kb-shail`.
- **Gemini API key** resolved securely from **AWS SSM Parameter Store**
  (`/investment-research/gemini-api-key`).

### Local (FastAPI) — the secondary path

- `src/main.py` — FastAPI app exposing `GET /` and `POST /analyze`.
- `src/agent/` — `agent.py`, `rag_engine.py`, `llm_service.py`, `compressor.py`.
- `src/rag/` — PDF loading, chunking, embeddings, FAISS build/retrieve.
- `src/tools/` — local equivalents of the market/news/RAG tools.

---

## 3. Features — Done ✅

### Core orchestration (AgentLambda)
- ✅ Keyword-based query classification (`market` / `news` / `rag`).
- ✅ Company + ticker extraction via `COMPANY_MAP` (NVIDIA, AMD, Intel).
- ✅ Synchronous child-lambda invocation with error handling.
- ✅ Context builder combining multi-tool output.
- ✅ Gemini LLM call with a structured research prompt.
- ✅ Handles both API Gateway proxy events and direct invocation.
- ✅ Structured JSON response (`answer`, `sources`, `used_tools`).
- ✅ Graceful fallbacks when a tool has no data.

### Market data
- ✅ Live quote fetch via `yfinance` (price, open, high, low, volume, market cap, P/E).

### News
- ✅ Top-5 headlines per company from Yahoo Finance RSS feeds.

### RAG / Retriever
- ✅ FAISS similarity search (top-5 chunks) over embedded documents.
- ✅ Index + metadata loaded from S3 with `/tmp` caching (warm-start reuse).
- ✅ Embedding service abstraction.
- ✅ Prebuilt artifacts present (`data/processed/`, `aws_artifacts/`: chunks, embeddings, metadata).
- ✅ Source PDFs available for NVIDIA, AMD, Intel (`data/raw/`).

### Local pipeline (src/)
- ✅ FastAPI service with `/analyze` endpoint.
- ✅ RAG engine with per-chunk compression before LLM synthesis.
- ✅ Reusable `LLMService` (loads key from `.env`).
- ✅ RAG build scripts (chunker, embeddings, FAISS build, PDF loader, text cleaner).

### Infrastructure & docs
- ✅ AWS SAM template (`template.yaml`) with 3 child lambdas + orchestrator + REST API.
- ✅ Least-privilege IAM (invoke-only on child lambdas, S3 read-only on retriever).
- ✅ Local test event files (`event.json`, `news_event.json`, `retriever_event.json`).
- ✅ README with deployment + usage instructions.
- ✅ Test scaffolding (`tests/test_llm.py`, `test_pdf_loader.py`, `test_rag.py`, `test_retriever.py`).

---

## 4. Features — Not Done / Gaps ⚠️

### Hardcoded / limited coverage
- ⚠️ **Only 3 companies** supported (NVIDIA, AMD, Intel) — `COMPANY_MAP` and news
  RSS feeds are hardcoded. No dynamic ticker resolution.
- ⚠️ **Keyword-based classification** is brittle — no LLM-based intent detection.
- ⚠️ Company extraction is regex/keyword only — misses aliases, misspellings, other tickers.

### RAG limitations
- ⚠️ RetrieverLambda expects `faiss_index.bin` in S3, but the checked-in artifacts are
  `embeddings.npy` + `chunks.json` + `metadata.json` — **the FAISS `.bin` build/upload
  step for the cloud path is not clearly wired up**.
- ⚠️ No re-ranking, relevance threshold, or chunk deduplication in the cloud retriever.
- ⚠️ Compression step exists only in the **local** RAG engine, not in the lambda path.

### Empty / unfinished areas
- ⚠️ `infra/cloudformation/` and `infra/terraform/` folders are **empty** (SAM is the only real IaC).
- ⚠️ `docs/` folder is **empty**.
- ⚠️ `src/utils/` appears unused/empty.
- ⚠️ Two implementations (`lambdas/` vs `src/`) partly duplicate logic and can drift.

### Robustness / production concerns
- ⚠️ No authentication / API key / rate limiting on the `/ask` endpoint.
- ⚠️ No caching of market/news results (every call hits external APIs).
- ⚠️ `yfinance` `.info` calls are slow and rate-limit-prone under Lambda's 20s timeout.
- ⚠️ No unit test coverage assertions verified against current lambda code.
- ⚠️ No CI/CD pipeline.
- ⚠️ No conversation memory / multi-turn context.
- ⚠️ No structured error/metrics/observability beyond basic CloudWatch logging.

### Requirements hygiene
- ⚠️ Root `requirements.txt` mixes serverless + local deps (`fastapi`, `uvicorn`) and lists
  `requests` twice. Per-lambda `requirements.txt` files are the deployable source of truth.

---

## 5. What The Project Requires

### To run locally (src/ FastAPI path)
- Python 3.12
- `pip install -r requirements.txt`
- A `.env` file with `GEMINI_API_KEY=<your-key>`
- Prebuilt RAG artifacts in `data/processed/` (present)
- Start: `python src/main.py` → open `http://localhost:8000/docs`

### To deploy to AWS (serverless path)
- **AWS CLI** installed and configured with credentials.
- **AWS SAM CLI** installed.
- **Python 3.12** runtime.
- **Google Gemini API key**.
- An **S3 bucket** (`investment-research-kb-shail`) containing:
  - `faiss_index.bin` (FAISS index)
  - `metadata.json` (chunk metadata)
- An **SSM SecureString parameter**: `/investment-research/gemini-api-key`.
- Build & deploy:
  ```bash
  sam build
  sam deploy --guided     # first time
  sam build && sam deploy # subsequent
  ```

### Key runtime dependencies
- `google-genai` — Gemini LLM client
- `faiss-cpu` + `numpy` — vector search
- `yfinance` — market data
- `feedparser` — news RSS
- `pdfplumber` — PDF parsing (RAG ingestion)
- `boto3` — AWS SDK (lambda invoke, S3)
- `fastapi` + `uvicorn` — local API (src only)

---

## 6. Suggested Next Steps (Priority Order)

1. **Fix the cloud RAG artifact gap** — ensure `faiss_index.bin` is built and uploaded to S3
   (add/verify the build+upload script), matching what `RetrieverLambda` loads.
2. **Generalize company support** — replace hardcoded `COMPANY_MAP`/RSS with dynamic ticker
   lookup so any company works.
3. **Upgrade query classification** — use Gemini (or a small model) for intent + entity
   extraction instead of keyword matching.
4. **Consolidate** the `src/` and `lambdas/` logic (shared core module) to prevent drift.
5. **Add caching + resilience** for market/news calls (respect Lambda timeout).
6. **Fill infra + docs** — either populate or remove the empty `cloudformation/`,
   `terraform/`, and `docs/` folders; clean up `requirements.txt`.
7. **Add auth + CI/CD** — secure the `/ask` endpoint and automate build/test/deploy.
8. **Verify test suite** runs against the current lambda code.
