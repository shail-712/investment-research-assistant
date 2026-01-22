import feedparser

RSS_FEEDS = {
    "NVIDIA": "https://finance.yahoo.com/rss/headline?s=NVDA",
    "AMD": "https://finance.yahoo.com/rss/headline?s=AMD",
    "INTEL": "https://finance.yahoo.com/rss/headline?s=INTC",
}

def get_news(company: str, max_items=5):
    feed_url = RSS_FEEDS.get(company.upper())
    if not feed_url:
        return []

    feed = feedparser.parse(feed_url)

    articles = []
    for entry in feed.entries[:max_items]:
        articles.append({
            "title": entry.title,
            "published": entry.get("published", ""),
            "summary": entry.get("summary", ""),
            "link": entry.link
            
        })

    return articles
