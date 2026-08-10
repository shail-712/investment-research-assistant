import json
import logging
import os
import boto3

from google.genai import Client
from google.genai.types import GenerateContentConfig

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")

GEMINI_API_KEY    = os.environ["GEMINI_API_KEY"]
gemini_client     = Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL      = "models/gemini-2.5-flash-lite-001"

MARKET_DATA_LAMBDA = os.environ.get("MARKET_DATA_LAMBDA", "MarketDataLambda")
NEWS_LAMBDA        = os.environ.get("NEWS_LAMBDA", "NewsLambda")
RETRIEVER_LAMBDA   = os.environ.get("RETRIEVER_LAMBDA", "RetrieverLambda")


# ════════════════════════════════════════════════════════════════════════════
# 1. CLASSIFY QUERY WITH GEMINI
#    Ask Gemini: "What ticker is this about, and what tools do we need?"
#    This replaces the old brittle keyword matching.
# ════════════════════════════════════════════════════════════════════════════

def classify_and_extract(query: str) -> dict:
    prompt = (
        "You are a query classifier for a stock research assistant.\n\n"
        "Given the user's question, return a JSON object with:\n"
        '- "ticker": the stock ticker symbol (e.g. "NVDA", "AAPL") or null if not identifiable\n'
        '- "company": the company name or null\n'
        '- "tools": a list chosen from ["market", "news", "rag"]\n'
        "  Use 'market' for: price, stock data, P/E ratio, market cap, volume\n"
        "  Use 'news' for: recent news, headlines, events\n"
        "  Use 'rag' for: earnings, revenue, annual reports, deep financials, guidance, comparison\n\n"
        f'Question: "{query}"\n\n'
        "Return ONLY valid JSON with no extra text."
    )
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            config=GenerateContentConfig(max_output_tokens=200, temperature=0.0),
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Gemini classification failed: {e}. Using RAG fallback.")
        return {"ticker": None, "company": None, "tools": ["rag"]}


# ════════════════════════════════════════════════════════════════════════════
# 2. INVOKE CHILD LAMBDAS
# ════════════════════════════════════════════════════════════════════════════

def invoke_lambda(function_name: str, payload: dict) -> dict | None:
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode(),
        )
        raw = json.loads(response["Payload"].read())
        # Unwrap "body" string if present (Lambda proxy response format)
        if "body" in raw:
            body = raw["body"]
            return json.loads(body) if isinstance(body, str) else body
        return raw
    except Exception as e:
        logger.error(f"Failed to invoke {function_name}: {e}")
        return None


def call_market_data(ticker: str) -> str:
    data = invoke_lambda(MARKET_DATA_LAMBDA, {"ticker": ticker})
    if not data:
        return f"[Market data unavailable for {ticker}]"
    return (
        f"Ticker: {data.get('ticker', ticker)}\n"
        f"  Price:      ${data.get('price', 'N/A')}\n"
        f"  Open:       ${data.get('open', 'N/A')}\n"
        f"  Day High:   ${data.get('high', 'N/A')}\n"
        f"  Day Low:    ${data.get('low', 'N/A')}\n"
        f"  Volume:     {data.get('volume', 'N/A')}\n"
        f"  Market Cap: ${data.get('market_cap', 'N/A')}\n"
        f"  P/E Ratio:  {data.get('pe_ratio', 'N/A')}\n"
    )


def call_news(ticker: str, company: str | None) -> str:
    label = company or ticker
    data = invoke_lambda(NEWS_LAMBDA, {"ticker": ticker})
    if not data or not data.get("articles"):
        return f"[No recent news found for {label}]"
    lines = [f"Latest news for {label}:"]
    for i, a in enumerate(data["articles"], 1):
        lines.append(f"  {i}. {a.get('title', 'No title')} ({a.get('published', '')})")
    return "\n".join(lines)


def call_rag(query: str) -> tuple[str, list[str]]:
    data = invoke_lambda(RETRIEVER_LAMBDA, {"query": query})
    if not data:
        return "[RAG retrieval unavailable]", []
    chunks = data if isinstance(data, list) else []
    sources: list[str] = []
    lines = ["Insights from financial documents:"]
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
# 3. SYNTHESIZE ANSWER WITH GEMINI
# ════════════════════════════════════════════════════════════════════════════

def call_gemini(query: str, context: str) -> str:
    prompt = (
        "You are an expert AI Investment Research Assistant.\n\n"
        f"USER QUESTION:\n{query}\n\n"
        "CONTEXT (from live market data, recent news, and financial documents):\n"
        f"{context}\n\n"
        "Instructions:\n"
        "- Answer the user's question based strictly on the context above.\n"
        "- Be factual, structured, and concise.\n"
        "- Use numbers and data where available.\n"
        "- If context is insufficient, say so clearly.\n"
        "- Format the response with sections if helpful."
    )
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            config=GenerateContentConfig(max_output_tokens=1024, temperature=0.7),
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini synthesis failed: {e}")
        return f"[LLM ERROR] Unable to generate answer: {e}"


# ════════════════════════════════════════════════════════════════════════════
# 4. LAMBDA HANDLER
# ════════════════════════════════════════════════════════════════════════════

def lambda_handler(event, context):
    # Parse query from API Gateway proxy event or direct invocation
    if "body" in event:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        query = body.get("query", "")
    else:
        query = event.get("query", "")

    if not query:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'query' field in request body"}),
        }

    logger.info(f"Query: {query}")

    # Step 1: Classify query and extract ticker using Gemini
    classification = classify_and_extract(query)
    ticker     = classification.get("ticker")
    company    = classification.get("company")
    tools      = classification.get("tools", ["rag"])
    logger.info(f"Classification: {classification}")

    # Step 2: Call the relevant tools
    context_sections: dict[str, str] = {}
    sources: list[str] = []
    used_tools: list[str] = []

    if "market" in tools and ticker:
        context_sections["Market Data"] = call_market_data(ticker)
        used_tools.append("market")

    if "news" in tools and ticker:
        context_sections["Recent News"] = call_news(ticker, company)
        used_tools.append("news")

    if "rag" in tools:
        rag_text, rag_sources = call_rag(query)
        context_sections["Financial Document Insights"] = rag_text
        sources.extend(rag_sources)
        used_tools.append("rag")

    if not context_sections:
        context_sections["Note"] = "No specific data could be fetched for this query."

    # Step 3: Build combined context string
    combined_context = "\n\n".join(
        f"## {title}\n{content}" for title, content in context_sections.items()
    )

    # Step 4: Synthesize answer
    answer = call_gemini(query, combined_context)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "answer": answer,
            "ticker": ticker,
            "company": company,
            "used_tools": used_tools,
            "sources": sources,
        }),
    }
