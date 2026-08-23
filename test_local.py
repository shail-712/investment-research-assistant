"""
test_local.py — Local test runner for Investment Research Assistant
====================================================================
Bypasses AWS/SAM/Docker entirely. Calls each lambda handler directly.

Usage:
    python test_local.py market         → test MarketDataLambda (NVDA)
    python test_local.py market AAPL    → test MarketDataLambda with custom ticker
    python test_local.py news           → test NewsLambda (NVIDIA)
    python test_local.py news AMD       → test NewsLambda with custom company
    python test_local.py retriever      → test RetrieverLambda (placeholder)
    python test_local.py agent          → test full Agent pipeline (NVDA stock price)
    python test_local.py agent "your query here"  → custom query
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Load .env manually (no dotenv library needed)
# ---------------------------------------------------------------------------
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
        print("[ENV] Loaded .env")
    else:
        print("[ENV] No .env file found — make sure GEMINI_API_KEY is set")

load_env()


# ---------------------------------------------------------------------------
# Pretty print helper
# ---------------------------------------------------------------------------
def print_result(label: str, result: dict):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    body = result.get("body")
    if body:
        try:
            parsed = json.loads(body)
            print(json.dumps(parsed, indent=2))
        except Exception:
            print(body)
    else:
        print(json.dumps(result, indent=2))
    status = result.get("statusCode", "?")
    print(f"\n  Status: {status}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# TEST: MarketDataLambda
# ---------------------------------------------------------------------------
def test_market(ticker: str = "NVDA"):
    print(f"\n[TEST] MarketDataLambda → ticker={ticker}")
    from lambdas.market_data.lambda_function import lambda_handler
    event = {"ticker": ticker}
    result = lambda_handler(event, None)
    print_result(f"MarketDataLambda | {ticker}", result)
    return result


# ---------------------------------------------------------------------------
# TEST: NewsLambda
# ---------------------------------------------------------------------------
def test_news(company: str = "NVIDIA"):
    print(f"\n[TEST] NewsLambda → company={company}")
    from lambdas.news.lambda_function import lambda_handler
    event = {"company": company}
    result = lambda_handler(event, None)
    print_result(f"NewsLambda | {company}", result)
    return result


# ---------------------------------------------------------------------------
# TEST: RetrieverLambda
# ---------------------------------------------------------------------------
def test_retriever(query: str = "What is NVIDIA's revenue?"):
    print(f"\n[TEST] RetrieverLambda → query={query}")
    from lambdas.retriever.lambda_function import lambda_handler
    event = {"query": query}
    result = lambda_handler(event, None)
    print_result(f"RetrieverLambda | {query}", result)
    return result


# ---------------------------------------------------------------------------
# TEST: Full Agent Pipeline (patched to call local functions directly)
# ---------------------------------------------------------------------------
def test_agent(query: str = "What is NVIDIA's current stock price?"):
    print(f"\n[TEST] AgentLambda (LOCAL) → query={query}")

    # Monkey-patch boto3 lambda invocations to call local handlers instead
    import unittest.mock as mock
    import json as _json

    from lambdas.market_data.lambda_function import lambda_handler as market_handler
    from lambdas.news.lambda_function import lambda_handler as news_handler
    from lambdas.retriever.lambda_function import lambda_handler as retriever_handler

    LAMBDA_MAP = {
        "MarketDataLambda": market_handler,
        "NewsLambda":       news_handler,
        "RetrieverLambda":  retriever_handler,
    }

    def fake_invoke(FunctionName, InvocationType, Payload):
        payload = _json.loads(Payload)
        handler = LAMBDA_MAP.get(FunctionName)
        if handler is None:
            return {"Payload": mock.MagicMock(read=lambda: _json.dumps({"error": "unknown lambda"}).encode())}
        result = handler(payload, None)
        result_bytes = _json.dumps(result).encode()
        return {"Payload": mock.MagicMock(read=lambda: result_bytes)}

    with mock.patch("lambdas.agent.lambda_function.lambda_client") as mock_client:
        mock_client.invoke.side_effect = fake_invoke
        from lambdas.agent.lambda_function import lambda_handler
        event = {"query": query}
        result = lambda_handler(event, None)

    print_result(f"AgentLambda (full pipeline) | {query}", result)
    return result


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == "market":
        ticker = args[1] if len(args) > 1 else "NVDA"
        test_market(ticker)

    elif cmd == "news":
        company = args[1] if len(args) > 1 else "NVIDIA"
        test_news(company)

    elif cmd == "retriever":
        query = args[1] if len(args) > 1 else "What is NVIDIA's revenue?"
        test_retriever(query)

    elif cmd == "agent":
        query = args[1] if len(args) > 1 else "What is NVIDIA's current stock price?"
        test_agent(query)

    else:
        print(f"[ERROR] Unknown command: '{cmd}'")
        print(__doc__)
        sys.exit(1)
