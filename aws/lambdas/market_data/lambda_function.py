from tools.market_data import get_market_data

def lambda_handler(event, context):
    ticker = event.get("ticker", "NVDA")
    return get_market_data(ticker)
