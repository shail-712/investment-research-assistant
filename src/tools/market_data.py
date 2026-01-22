import yfinance as yf

def get_market_data(ticker: str):
    ticker = ticker.upper()
    stock = yf.Ticker(ticker)

    info = stock.info

    return {
        "ticker": ticker,
        "price": info.get("currentPrice"),
        "market_cap": info.get("marketCap"),
        "volume": info.get("volume"),
        "pe_ratio": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        
        
    }
