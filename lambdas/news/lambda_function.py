from tools.news_tool import get_news

def lambda_handler(event, context):
    company = event.get("company", "NVIDIA")
    return get_news(company)
