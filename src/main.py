import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from agent.agent import analyze_query
from rag.faiss_retriever import retrieve_chunks

class QueryRequest(BaseModel):
    query: str

app = FastAPI(title="AI Investment Research Agent")


@app.get("/")
async def home():
    return {
        "project": "AI Investment Research Agent",
        "status": "running",
        "message": "Go to /docs for API usage."
    }


@app.post("/analyze")
async def analyze(request: QueryRequest):
    rag_results = retrieve_chunks(request.query)
    result = analyze_query(request.query, rag_results)
    return {"result": result}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
