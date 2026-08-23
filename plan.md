# Investment Research Assistant — Project Plan

> **How to use this file:** After each completed task, update the checkbox (`[ ]` → `[x]`) and note what was built. This is your living record of what has been done and what is left.

---

## What This Project Is (Plain English)

You're building an AI-powered investment research assistant. The core problem: answering a financial question (e.g. "How does NVIDIA's revenue compare to AMD?") requires combining three different data sources — live stock prices, recent news, and actual financial filing documents — all at once.

The solution: one natural-language question goes in, the system automatically figures out which sources are needed, pulls data from all of them in parallel, and hands everything to Google Gemini to produce a single, structured answer.

**The final architecture:**
```
User ──POST /ask──► API Gateway ──► AgentLambda (orchestrator)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
             MarketDataLambda       NewsLambda         RetrieverLambda
              (yfinance)          (Yahoo RSS)          (FAISS + S3)
                    │                    │                    │
                    └────────────────────┴────────────────────┘
                                         ▼
                                Gemini 2.5 Flash Lite
                                         ▼
                            Structured JSON answer
                            { answer, sources, used_tools }
```

---

## Current State Snapshot (as of Phase 2 in progress)

| Component | File | Status |
|-----------|------|--------|
| Orchestrator / AgentLambda | `lambdas/agent/lambda_function.py` | ✅ Built |
| Query classification (keyword) | inside AgentLambda | ✅ Built |
| Company + ticker extraction | inside AgentLambda | ✅ Built |
| Child-lambda invocation via boto3 | inside AgentLambda | ✅ Built |
| Gemini synthesis call | inside AgentLambda | ✅ Built |
| MarketDataLambda | `lambdas/market_data/lambda_function.py` | ✅ Built |
| NewsLambda | `lambdas/news/lambda_function.py` | ✅ Built |
| RetrieverLambda (stub) | `lambdas/retriever/lambda_function.py` | ⚠️ Basic skeleton only |
| FAISS build + upload pipeline | `src/rag/build_faiss.py` | ✅ Built |
| FAISS index artifact | `data/processed/faiss_index.bin` | ✅ Exists locally |
| Local test runner | `test_local.py` | ✅ Built |
| Local testing commands | `TESTING.md` | ✅ Written |
| SAM template | `template.yaml` | ✅ Defined (pending new AWS account) |
| DynamoDB caching | — | ❌ Not started |
| API Gateway auth (API keys) | — | ❌ Not started |
| Deployment to AWS | — | ⏸️ Paused (new AWS account needed) |

---

## Phase 1 — Agent Orchestrator with Gemini Classification ✅ DONE

**What was built:** The brain of the system. The orchestrator (`AgentLambda`) that receives a user question, decides which tools to call, calls them, combines the results, and asks Gemini to write the final answer.

### Task 1.1 — Query Classification ✅
- [x] Keyword-based tool router: routes to `market`, `news`, or `rag` based on what words appear in the query
- [x] `extract_company()` — recognizes NVIDIA / AMD / Intel by name or ticker
- [x] Handles both API Gateway proxy events and direct Lambda invocations

### Task 1.2 — Child-Lambda Invocation ✅
- [x] `invoke_lambda()` — generic boto3 wrapper to call any child Lambda synchronously
- [x] `call_market_data()`, `call_news()`, `call_rag()` — specific callers with formatted output
- [x] Graceful fallback strings when a child Lambda fails

### Task 1.3 — Gemini Synthesis ✅
- [x] `call_gemini()` — takes combined context and user query, returns a structured answer
- [x] Prompt engineered to cite data, use numbers, and structure the response

### Task 1.4 — FAISS Build + Upload Pipeline ✅
- [x] `src/rag/build_faiss.py` — builds `faiss_index.bin` from `embeddings.npy`
- [x] `--test` flag runs a self-test search to verify index/metadata alignment
- [x] `--upload` flag pushes the index and metadata to S3 so RetrieverLambda can load them
- [x] `data/processed/faiss_index.bin` confirmed present locally

---

## Phase 2 — Child Lambdas: Market Data, News, Retriever + FAISS Pipeline ← NEXT

**What this phase does:** The three child lambdas are currently basic skeletons. This phase makes each one production-ready: proper error handling, correct response format, the balanced-retrieval fix for the RAG, and the full /tmp warm-start caching.

### Task 2.1 — MarketDataLambda: Full Implementation ✅ DONE
**File:** `lambdas/market_data/lambda_function.py`

**Why:** Previously used `stock.info` for most fields, which is the slow call. Also had no logging or graceful error handling.

- [x] Switch all fields to `fast_info` where available (price, volume, market cap, high, low)
- [x] Keep only `.info` for fields not in `fast_info` (P/E) — isolated in its own try/except so it can't crash the response
- [x] Add structured logging (so CloudWatch shows what happened)
- [x] Validate ticker input; return clean error JSON if missing
- [x] Return consistent JSON format that AgentLambda already expects: `{ ticker, price, open, high, low, volume, market_cap, pe_ratio }`

**Resume bullet unlocked:**
> "I traced part of the latency to yfinance's stock.info call and switched to fast_info, which brought observed development latency down significantly."

### Task 2.2 — NewsLambda: Full Implementation ✅ DONE
**File:** `lambdas/news/lambda_function.py`

**Why:** Previously only returned titles. No link, no error handling if the RSS feed was unreachable.

- [x] Return full article objects: `{ title, link, published, summary }` (summary from RSS `<description>` tag)
- [x] Handle feedparser timeout / empty feed gracefully — socket timeout guard + `bozo` check
- [x] Add logging
- [x] Keep top-5 articles as default but make it configurable via `count` field in event payload
- [x] Case-insensitive company name input ("nvidia", "NVIDIA", "Nvidia" all work)

### Task 2.3 — RetrieverLambda: Full Implementation with Balanced Retrieval
**File:** `lambdas/retriever/lambda_function.py`

**Why:** Two problems with the current skeleton: (1) no `/tmp` caching — it downloads the FAISS index on every call. (2) When comparing two companies, all top-5 results can be from the same company.

- [ ] Implement `/tmp` warm-start caching: check if `index` is `None` before downloading from S3
- [ ] **Balanced retrieval fix:** over-fetch top 50 candidates, then cap to 3 chunks per company before returning
  - This is the fix for "comparing NVIDIA and AMD gets all NVIDIA results"
- [ ] Make embedding service production-safe (timeout guard, error fallback)
- [ ] Return consistent format: list of `{ company, filename, text, score }`
- [ ] Add logging

**Resume bullet unlocked:**
> "When comparing two companies, the top FAISS results could all belong to one company. So instead of taking only the top results, I over-fetch around 50 candidates and then limit the number of chunks per company."

### Task 2.4 — Embedding Service for RetrieverLambda
**File:** `lambdas/retriever/embedding_service.py`

**Why:** This file exists as a stub but needs a real implementation so FAISS search can work in the cloud.

- [ ] Implement `EmbeddingService.embed(text: str) -> list[float]` using Gemini Embedding API (`text-embedding-004`)
- [ ] Use module-level client instantiation (reused across warm invocations)
- [ ] Handle API errors gracefully

---

## Phase 3 — DynamoDB Caching Layer for Market Data and News

**What this phase does:** Right now, every call to MarketDataLambda hits yfinance, and every call to NewsLambda hits the RSS feed. DynamoDB caching means: check DynamoDB first → if fresh data exists, return it immediately → only call the external source when needed or when the cache is stale.

**Why this matters:** Rate-limit protection, faster responses, less external dependency.

**Resume bullet unlocked:**
> "Added a DynamoDB caching layer for market data and news lookups, reducing redundant API calls and third-party rate-limit failures."

### Task 3.1 — DynamoDB Table Definition in SAM Template
**File:** `template.yaml`

- [ ] Add a `CacheTable` resource (DynamoDB, On-Demand billing mode, Free Tier)
- [ ] Schema: `pk` (String, partition key) — e.g., `MARKET#NVDA`, `NEWS#NVIDIA`
- [ ] Add `ttl` attribute for TTL expiry (DynamoDB's native TTL feature)
- [ ] Grant MarketDataLambda and NewsLambda read+write access to the table

### Task 3.2 — Cache Logic in MarketDataLambda
**File:** `lambdas/market_data/lambda_function.py`

- [ ] On invocation: check DynamoDB for key `MARKET#{ticker}`
- [ ] If found and TTL not expired: return cached data immediately
- [ ] If not found or stale: call yfinance, write result to DynamoDB with a 15-minute TTL, return result
- [ ] TTL calculation: `int(time.time()) + 900` (15 minutes)

### Task 3.3 — Cache Logic in NewsLambda
**File:** `lambdas/news/lambda_function.py`

- [ ] On invocation: check DynamoDB for key `NEWS#{company}`
- [ ] If found and TTL not expired: return cached data immediately
- [ ] If not found or stale: fetch RSS, write to DynamoDB with a 30-minute TTL, return result

---

## Phase 4 — API Gateway + SAM Template + Deploy

**What this phase does:** Wire everything together and actually deploy to AWS. Add API key authentication. Then run a full end-to-end test from a real HTTP request.

**Resume bullet unlocked:**
> "Secured the /ask API endpoint using API Gateway Usage Plans with key-based authentication, preventing unauthenticated access. Configured request throttling and burst limits to protect downstream Lambdas and the Gemini API."

### Task 4.1 — Complete the SAM Template
**File:** `template.yaml`

- [ ] Add `CACHE_TABLE` environment variable to MarketDataLambda and NewsLambda
- [ ] Add DynamoDBCrudPolicy for MarketDataLambda and NewsLambda
- [ ] Fix the `AgentAPI` resource — consolidate the duplicate Swagger + Events API definition
- [ ] Set proper timeouts per Lambda (RetrieverLambda needs more time on cold start)

### Task 4.2 — API Gateway Authentication (Usage Plans + API Keys)
**File:** `template.yaml`

- [ ] Add `ApiKey` resource and `UsagePlan` resource to the SAM template
- [ ] Require API key on the `POST /ask` route (via `x-api-key` header)
- [ ] Set throttling: e.g., 10 req/sec steady, 20 burst
- [ ] Document how to retrieve the generated API key post-deploy

### Task 4.3 — Preflight Checks Before Deploy

- [ ] Verify AWS credentials: `aws sts get-caller-identity`
- [ ] Confirm or create S3 bucket `investment-research-kb-shail`
- [ ] Confirm SSM parameter `/investment-research/gemini-api-key` is set
- [ ] Upload FAISS index: `python src/rag/build_faiss.py --upload --bucket investment-research-kb-shail`

### Task 4.4 — First Deploy

- [ ] `sam build` — package all four Lambdas with dependencies
- [ ] `sam deploy --guided` — first-time deploy, creates CloudFormation stack
- [ ] Record the API Gateway endpoint URL from deploy output

### Task 4.5 — End-to-End Test

- [ ] Market query: `POST /ask { "query": "What is NVIDIA's current stock price?" }` → `used_tools: ["market"]`
- [ ] News query: `POST /ask { "query": "Any recent NVIDIA news?" }` → `used_tools: ["news"]`
- [ ] RAG query: `POST /ask { "query": "What is NVIDIA's revenue guidance?" }` → `used_tools: ["rag"]`
- [ ] Comparison query: `POST /ask { "query": "Compare NVIDIA and AMD revenue" }` → chunks from both companies in sources
- [ ] Auth test: call without `x-api-key` header → should get 403 Forbidden

---

## Optional / Future Enhancements (Not Required)

| Enhancement | What it does |
|-------------|-------------|
| LLM-based query classification | Replace keyword matching with a Gemini call returning structured JSON `{ tools, ticker, company }` |
| Conversation memory | Pass prior Q&A turns in the Gemini prompt |
| More companies | Extend beyond 3 hardcoded companies |
| CI/CD pipeline | GitHub Actions: lint → test → sam build → sam deploy |
| Observability | X-Ray tracing + CloudWatch dashboards |

---

## Key Files Quick Reference

| File | What it does |
|------|-------------|
| `lambdas/agent/lambda_function.py` | Orchestrator — the brain. Routes queries, calls children, synthesizes with Gemini |
| `lambdas/market_data/lambda_function.py` | Fetches live stock data via yfinance |
| `lambdas/news/lambda_function.py` | Fetches top-5 news headlines via Yahoo Finance RSS |
| `lambdas/retriever/lambda_function.py` | FAISS vector search over financial filings |
| `lambdas/retriever/embedding_service.py` | Converts query text → embedding vector |
| `src/rag/build_faiss.py` | One-time script: builds FAISS index, optionally uploads to S3 |
| `template.yaml` | AWS SAM infrastructure: all 4 Lambdas + API Gateway |
| `data/processed/` | Local artifacts: chunks, embeddings, FAISS index, metadata |
