import json
import logging
import os
import re
import boto3

from google.genai import Client
from google.genai.types import GenerateContentConfig

# ─── Logging ────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ─── AWS Lambda Client ───────────────────────────────────────────────────────
lambda_client = boto3.client("lambda")

# ─── Gemini Client ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_client = Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "models/gemini-2.5-flash-lite-001"
GEMINI_CONFIG = GenerateContentConfig(max_output_tokens=1024, temperature=0.7)

# ─── Lambda Function Names (from env or default SAM names) ───────────────────
MARKET_DATA_LAMBDA = os.environ.get("MARKET_DATA_LAMBDA", "MarketDataLambda")
NEWS_LAMBDA        = os.environ.get("NEWS_LAMBDA", "NewsLambda")
RETRIEVER_LAMBDA   = os.environ.get("RETRIEVER_LAMBDA", "RetrieverLambda")

# ─── Known Companies ─────────────────────────────────────────────────────────
COMPANY_MAP = {
    "nvidia": {"name": "NVIDIA", "ticker": "NVDA"},
    "nvda":   {"name": "NVIDIA", "ticker": "NVDA"},
    "amd":    {"name": "AMD",    "ticker": "AMD"},
    "intel":  {"name": "Intel",  "ticker": "INTC"},
    "intc":   {"name": "Intel",  "ticker": "INTC"},
}

# ════════════════════════════════════════════════════════════════════════════
# 1. QUERY CLASSIFICATION
# ════════════════════════════════════════════════════════════════════════════

def classify_query(query: str) -> list[str]:
    """
    Returns a list of tools to use based on keyword matching.
    Possible values: 'market', 'news', 'rag'
    """
    q = query.lower()
    tools = []

    if any(kw in q for kw in ["price", "stock", "pe", "market cap", "volume", "eps", "marketcap"]):
        tools.append("market")

    if any(kw in q for kw in ["news", "latest", "recent", "headline", "article"]):
        tools.append("news")

    if not tools:
        tools.append("rag")   # default fallback

    # Also add RAG for deep financial analysis keywords
    if any(kw in q for kw in ["revenue", "earnings", "profit", "quarter", "annual", "forecast", "guidance", "compare", "analysis"]):
        if "rag" not in tools:
            tools.append("rag")

    return tools


# ════════════════════════════════════════════════════════════════════════════
# 2. COMPANY EXTRACTION
# ════════════════════════════════════════════════════════════════════════════

def extract_company(query: str) -> dict | None:
    """
    Extracts company name and ticker from the query.
    Returns dict like {"name": "NVIDIA", "ticker": "NVDA"} or None.
    """
    q = query.lower()
    for keyword, info in COMPANY_MAP.items():
        if re.search(r'\b' + keyword + r'\b', q):
            return info
    return None


# ════════════════════════════════════════════════════════════════════════════
# 3. TOOL CALLERS
# ════════════════════════════════════════════════════════════════════════════

def invoke_lambda(function_name: str, payload: dict) -> dict | None:
    """
    Invokes another Lambda function synchronously via boto3.
    Returns parsed JSON body or None on failure.
    """
    try:
        logger.info(f"Invoking Lambda: {function_name} with payload: {payload}")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        raw = response["Payload"].read()
        result = json.loads(raw)

        # Lambda response wraps output in "body"
        if "body" in result:
            return json.loads(result["body"])
        return result

    except Exception as e:
        logger.error(f"Failed to invoke {function_name}: {e}")
        return None


def call_market_data(ticker: str) -> str:
    """Calls MarketDataLambda and returns a formatted string."""
    data = invoke_lambda(MARKET_DATA_LAMBDA, {"ticker": ticker})
    if not data:
        return f"[Market data unavailable for {ticker}]"

    return (
        f"Ticker: {data.get('ticker', ticker)}\n"
        f"  Price:      ${data.get('price', 'N/A')}\n"
        f"  Open:       ${data.get('open', 'N/A')}\n"
        f"  High:       ${data.get('high', 'N/A')}\n"
        f"  Low:        ${data.get('low', 'N/A')}\n"
        f"  Volume:     {data.get('volume', 'N/A')}\n"
        f"  Market Cap: ${data.get('market_cap', 'N/A')}\n"
        f"  P/E Ratio:  {data.get('pe_ratio', 'N/A')}\n"
    )


def call_news(company_name: str) -> str:
    """Calls NewsLambda and returns a formatted string of headlines."""
    data = invoke_lambda(NEWS_LAMBDA, {"company": company_name})
    if not data or "articles" not in data:
        return f"[News unavailable for {company_name}]"

    articles = data["articles"]
    if not articles:
        return f"[No recent news found for {company_name}]"

    lines = [f"Latest news for {company_name}:"]
    for i, a in enumerate(articles, 1):
        lines.append(f"  {i}. {a.get('title', 'No title')} ({a.get('published', '')})")
    return "\n".join(lines)


def call_rag(query: str) -> tuple[str, list]:
    """
    Calls RetrieverLambda and returns (formatted_string, sources_list).
    """
    data = invoke_lambda(RETRIEVER_LAMBDA, {"query": query})
    if not data:
        return "[RAG retrieval unavailable]", []

    # data is a list of chunk dicts from the retriever
    chunks = data if isinstance(data, list) else []
    sources = []
    lines = ["RAG Insights from financial documents:"]

    for chunk in chunks:
        company  = chunk.get("company", "Unknown")
        filename = chunk.get("filename", "")
        text     = chunk.get("text", "").strip()
        if text:
            lines.append(f"  [{company} | {filename}]: {text[:300]}...")
            src = f"{company} – {filename}"
            if src not in sources:
                sources.append(src)

    return "\n".join(lines), sources


# ════════════════════════════════════════════════════════════════════════════
# 4. CONTEXT BUILDER
# ════════════════════════════════════════════════════════════════════════════

def build_context(sections: dict[str, str]) -> str:
    """
    Combines tool outputs into a single context string for the LLM.
    sections = {"Market Data": "...", "News": "...", "RAG Insights": "..."}
    """
    parts = []
    for title, content in sections.items():
        if content:
            parts.append(f"## {title}\n{content}")
    return "\n\n".join(parts)


# ════════════════════════════════════════════════════════════════════════════
# 5. LLM CALL
# ════════════════════════════════════════════════════════════════════════════

def call_gemini(query: str, context: str) -> str:
    """Sends the user query + collected context to Gemini and returns the answer."""
    prompt = f"""You are an expert AI Investment Research Assistant.

USER QUESTION:
{query}

CONTEXT (from live market data, news, and financial documents):
{context}

Instructions:
- Answer the user's question based strictly on the context above.
- Be factual, structured, and concise.
- Use numbers and data where available.
- If context is insufficient, say so clearly.
- Format the response with sections if helpful.
"""
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            config=GEMINI_CONFIG,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini LLM call failed: {e}")
        return f"[LLM ERROR] Unable to generate answer: {str(e)}"


# ════════════════════════════════════════════════════════════════════════════
# 6. MAIN HANDLER
# ════════════════════════════════════════════════════════════════════════════

def lambda_handler(event, context):
    logger.info(f"Agent Lambda invoked. Event: {json.dumps(event)}")

    # ── Parse input ──────────────────────────────────────────────────────────
    # Support both direct invocation and API Gateway proxy events
    if "body" in event:
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            return _error_response(400, "Invalid JSON in request body")
    else:
        body = event

    query = body.get("query", "").strip()
    if not query:
        return _error_response(400, "Missing required field: 'query'")

    logger.info(f"Processing query: {query}")

    # ── Classify query ───────────────────────────────────────────────────────
    tools_to_use = classify_query(query)
    company_info = extract_company(query)
    logger.info(f"Tools selected: {tools_to_use} | Company: {company_info}")

    # ── Call tools ───────────────────────────────────────────────────────────
    context_sections = {}
    sources = []
    used_tools = []

    if "market" in tools_to_use:
        ticker = company_info["ticker"] if company_info else None
        if ticker:
            logger.info(f"Calling MarketDataLambda for ticker: {ticker}")
            context_sections["Market Data"] = call_market_data(ticker)
            used_tools.append("market")
        else:
            logger.warning("Market tool selected but no ticker found in query; skipping.")

    if "news" in tools_to_use:
        company_name = company_info["name"] if company_info else None
        if company_name:
            logger.info(f"Calling NewsLambda for company: {company_name}")
            context_sections["News"] = call_news(company_name)
            used_tools.append("news")
        else:
            logger.warning("News tool selected but no company found in query; skipping.")

    if "rag" in tools_to_use:
        logger.info("Calling RetrieverLambda for RAG retrieval")
        rag_text, rag_sources = call_rag(query)
        context_sections["RAG Insights"] = rag_text
        sources.extend(rag_sources)
        used_tools.append("rag")

    # ── Build context & call LLM ─────────────────────────────────────────────
    if not context_sections:
        # Fallback: if no tool could run, still try LLM with just the query
        logger.warning("No tools produced output. Running LLM with empty context.")
        combined_context = "No additional context available."
    else:
        combined_context = build_context(context_sections)

    logger.info("Calling Gemini LLM...")
    answer = call_gemini(query, combined_context)

    # ── Return structured response ───────────────────────────────────────────
    result = {
        "answer": answer,
        "sources": sources,
        "used_tools": used_tools,
    }

    logger.info(f"Agent Lambda completed. Tools used: {used_tools}")
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result),
    }


def _error_response(status_code: int, message: str) -> dict:
    logger.error(f"Error {status_code}: {message}")
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
