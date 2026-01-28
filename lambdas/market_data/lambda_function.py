import json
import yfinance as yf

def lambda_handler(event, context):
    try:
        # 1. Get ticker from event
        ticker = event.get("ticker")
        if not ticker:
            return {"error": "No ticker provided"}

        # 2. Fetch data using yfinance
        stock = yf.Ticker(ticker)

        price = stock.fast_info.get("last_price")
        volume = stock.fast_info.get("last_volume")
        open_price = stock.info.get("open")
        high = stock.info.get("dayHigh")
        low = stock.info.get("dayLow")
        market_cap = stock.info.get("marketCap")
        pe_ratio = stock.info.get("trailingPE")

        # 3. Build response
        data = {
            "ticker": ticker,
            "price": price,
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
        }

        return {
            "statusCode": 200,
            "body": json.dumps(data)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
