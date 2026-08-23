# Local Testing Commands
> All commands run from the project root: `c:\Shail\Projects\investment-research-assistant`

---

## 1. Setup (run once)

```powershell
# Install all dependencies
pip install -r requirements.txt

# Verify .env has your Gemini API key
cat .env
```

---

## 2. Test MarketDataLambda

```powershell
# Default: NVDA
python test_local.py market

# Custom ticker
python test_local.py market AAPL
python test_local.py market AMD
python test_local.py market INTC
```

---

## 3. Test NewsLambda

```powershell
# Default: NVIDIA
python test_local.py news

# Custom company
python test_local.py news AMD
python test_local.py news Intel
```

---

## 4. Test RetrieverLambda (RAG)

```powershell
# Default query
python test_local.py retriever

# Custom query
python test_local.py retriever "What is AMD's revenue guidance?"
```

---

## 5. Test Full Agent Pipeline (end-to-end)

```powershell
# Market query
python test_local.py agent "What is NVIDIA's current stock price?"

# News query
python test_local.py agent "What is the latest news for AMD?"

# RAG / analysis query
python test_local.py agent "What is NVIDIA's revenue guidance?"

# Combined query (market + news + RAG)
python test_local.py agent "Compare NVIDIA and AMD revenue"
```

---

## 6. Quick one-liners (no test script needed)

```powershell
# MarketData direct
python -c "from lambdas.market_data.lambda_function import lambda_handler; import json, os; os.environ['GEMINI_API_KEY']=''; print(json.dumps(lambda_handler({'ticker':'NVDA'}, None), indent=2))"

# News direct
python -c "from lambdas.news.lambda_function import lambda_handler; import json; print(json.dumps(lambda_handler({'company':'NVIDIA'}, None), indent=2))"
```

---

## 7. When ready to deploy to AWS

```powershell
# 1. Configure CLI with new account
aws configure

# 2. Add Gemini key to SSM
aws ssm put-parameter --name "/investment-research/gemini-api-key" --value "YOUR_KEY" --type SecureString

# 3. Create S3 bucket for knowledge base
aws s3 mb s3://investment-research-kb-shail --region ap-south-1

# 4. Build and deploy
sam build
sam deploy --guided
```

---

## Notes
- `template.yaml` is kept untouched for when you log into the new AWS account.
- The `.aws-sam` build folder has been deleted — `sam build` will recreate it.
- `test_local.py` patches boto3 so the agent calls local Python functions directly (no cloud needed).
