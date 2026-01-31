import json
import feedparser

# Free financial RSS sources
RSS_FEEDS = {
    "NVIDIA": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
    "AMD": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMD&region=US&lang=en-US",
    "Intel": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=INTC&region=US&lang=en-US",
}

def lambda_handler(event, context):
    company = event.get("company")

    if not company or company not in RSS_FEEDS:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid or missing company"})
        }

    feed = feedparser.parse(RSS_FEEDS[company])

    articles = []
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.get("published", "")
        })  

    return {
        "statusCode": 200,
        "body": json.dumps({
            "company": company,
            "articles": articles
        })
    }
