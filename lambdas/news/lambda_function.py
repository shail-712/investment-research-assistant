import json
import logging
import socket
import feedparser

# ---------------------------------------------------------------------------
# Logging — CloudWatch picks this up automatically
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# RSS Feed registry
# Add more companies here without touching handler logic.
# ---------------------------------------------------------------------------
RSS_FEEDS = {
    "NVIDIA": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US",
    "AMD":    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMD&region=US&lang=en-US",
    "INTEL":  "https://feeds.finance.yahoo.com/rss/2.0/headline?s=INTC&region=US&lang=en-US",
}

# Keywords used to filter RSS results — Yahoo's feed returns loosely related
# market news, so we only keep articles that mention the company/ticker by name.
COMPANY_KEYWORDS = {
    "NVIDIA": {"nvidia", "nvda"},
    "AMD":    {"amd"},
    "INTEL":  {"intel", "intc"},
}

# How many articles to return by default (caller can override via event)
DEFAULT_ARTICLE_COUNT = 5

# Feedparser socket timeout in seconds (prevents hanging on slow feeds)
FEED_TIMEOUT_SECONDS = 8


def lambda_handler(event, context):
    """
    NewsLambda — fetches latest news articles for a given company via RSS.

    Expected input:
        { "company": "NVIDIA" }                      # returns top 5
        { "company": "AMD", "count": 3 }             # returns top 3

    Returns:
        {
            "statusCode": 200,
            "body": "{
                \"company\": \"NVIDIA\",
                \"articles\": [
                    {
                        \"title\": \"...\",
                        \"link\": \"...\",
                        \"published\": \"...\",
                        \"summary\": \"...\"
                    },
                    ...
                ]
            }"
        }
    """

    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    company_raw = event.get("company")
    if not company_raw:
        logger.warning("NewsLambda called with no company in event: %s", event)
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing required field: 'company'"}),
        }

    # Normalise casing — accept "nvidia", "NVIDIA", "Nvidia" etc.
    company = company_raw.strip().upper()
    if company not in RSS_FEEDS:
        logger.warning("Unknown company requested: '%s'. Known: %s", company, list(RSS_FEEDS.keys()))
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Unknown company '{company}'. Supported: {list(RSS_FEEDS.keys())}"
            }),
        }

    count = int(event.get("count", DEFAULT_ARTICLE_COUNT))
    logger.info("Fetching top-%d articles for company: %s", count, company)

    # ------------------------------------------------------------------
    # 2. Fetch RSS feed with timeout guard
    # ------------------------------------------------------------------
    feed_url = RSS_FEEDS[company]
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(FEED_TIMEOUT_SECONDS)
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.error("RSS fetch failed for %s: %s", company, e)
        return {
            "statusCode": 502,
            "body": json.dumps({"error": f"Failed to fetch RSS feed: {str(e)}"}),
        }
    finally:
        socket.setdefaulttimeout(old_timeout)

    # ------------------------------------------------------------------
    # 3. Handle empty / unreachable feed
    # ------------------------------------------------------------------
    if feed.bozo and not feed.entries:
        logger.error("RSS feed malformed or unreachable for %s: %s", company, feed.bozo_exception)
        return {
            "statusCode": 502,
            "body": json.dumps({"error": "RSS feed unreachable or returned no entries"}),
        }

    if not feed.entries:
        logger.warning("RSS feed returned 0 entries for %s", company)
        return {
            "statusCode": 200,
            "body": json.dumps({"company": company, "articles": []}),
        }

    # ------------------------------------------------------------------
    # 4. Parse articles — over-fetch, title-filter, then cap to count
    # ------------------------------------------------------------------
    keywords = COMPANY_KEYWORDS[company]

    # Over-fetch up to 20 so we still have enough after title filtering
    raw_articles = []
    for entry in feed.entries[:20]:
        raw_articles.append({
            "title":     entry.get("title", "No title"),
            "link":      entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary":   entry.get("summary", entry.get("description", "")).strip() or None,
        })

    # Keep only articles that mention the company name or ticker in the title
    filtered = [
        a for a in raw_articles
        if any(kw in a["title"].lower() for kw in keywords)
    ]

    logger.info(
        "Title filter: %d/%d articles kept for %s (keywords: %s)",
        len(filtered), len(raw_articles), company, keywords,
    )

    articles = filtered[:count]

    return {
        "statusCode": 200,
        "body": json.dumps({
            "company":  company,
            "articles": articles,
        }),
    }
