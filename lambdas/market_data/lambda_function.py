import json
import logging
import yfinance as yf

# ---------------------------------------------------------------------------
# Logging — CloudWatch picks this up automatically
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    MarketDataLambda — fetches live market data for a given ticker.

    Expected input (direct invocation or from AgentLambda):
        { "ticker": "NVDA" }

    Returns:
        {
            "statusCode": 200,
            "body": "{\"ticker\": \"NVDA\", \"price\": ..., \"open\": ..., ...}"
        }

    Performance note:
        fast_info is used for price, volume, high, low, and market_cap
        because it makes a single lightweight HTTP request.
        .info is only called for trailingPE, which isn't available in fast_info.
        This significantly reduces cold-start and warm-call latency compared
        to fetching everything from .info.
    """

    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    ticker_raw = event.get("ticker")
    if not ticker_raw:
        logger.warning("MarketDataLambda called with no ticker in event: %s", event)
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing required field: 'ticker'"}),
        }

    ticker = ticker_raw.strip().upper()
    logger.info("Fetching market data for ticker: %s", ticker)

    # ------------------------------------------------------------------
    # 2. Fetch data — fast_info first (single lightweight call)
    # ------------------------------------------------------------------
    try:
        stock = yf.Ticker(ticker)
        fi = stock.fast_info

        price      = fi.get("lastPrice")
        day_high   = fi.get("dayHigh")
        day_low    = fi.get("dayLow")
        volume     = fi.get("lastVolume")
        market_cap = fi.get("marketCap")

        # open is not reliably in fast_info — pull from info
        open_price = fi.get("open")

        logger.info(
            "fast_info fetched | price=%.2f high=%.2f low=%.2f vol=%s mcap=%s",
            price or 0, day_high or 0, day_low or 0, volume, market_cap,
        )

    except Exception as e:
        logger.error("fast_info fetch failed for %s: %s", ticker, e)
        return {
            "statusCode": 502,
            "body": json.dumps({"error": f"Failed to fetch market data: {str(e)}"}),
        }

    # ------------------------------------------------------------------
    # 3. Fetch PE ratio separately — .info is slower but PE isn't in fast_info
    #    Wrapped in its own try/except so a PE failure never kills the response.
    # ------------------------------------------------------------------
    pe_ratio = None
    try:
        pe_ratio = stock.info.get("trailingPE")
        logger.info("PE ratio fetched: %s", pe_ratio)
    except Exception as e:
        logger.warning("Could not fetch PE ratio for %s (non-fatal): %s", ticker, e)

    # ------------------------------------------------------------------
    # 4. Build and return response
    # ------------------------------------------------------------------
    data = {
        "ticker":     ticker,
        "price":      price,
        "open":       open_price,
        "high":       day_high,
        "low":        day_low,
        "volume":     volume,
        "market_cap": market_cap,
        "pe_ratio":   pe_ratio,
    }

    logger.info("MarketDataLambda success for %s: %s", ticker, data)
    return {
        "statusCode": 200,
        "body": json.dumps(data),
    }
