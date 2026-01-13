from agent.llm_service import LLMService

llm = LLMService()

def analyze_query(query, rag_results):
    prompt = f"""
You are an AI Investment Research Assistant.

User query: {query}

RAG results: {rag_results}

Provide a short, clean, structured analysis.
"""
    return llm.generate(prompt)
