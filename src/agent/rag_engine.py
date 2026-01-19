from src.rag.faiss_retriever import retrieve_chunks
from src.agent.llm_service import LLMService
from src.agent.compressor import Compressor

class RAGEngine:
    def __init__(self):
        self.llm = LLMService()
        self.compressor = Compressor()

    def answer(self, query: str):
        chunks = retrieve_chunks(query)

        # Compress each chunk (2–3 sentences each)
        compressed_evidence = []
        for c in chunks:
            summary = self.compressor.compress(c["text"])
            compressed_evidence.append(
                f"{c['company']} ({c['filename']}): {summary}"
            )

        context_text = "\n".join(compressed_evidence)

        prompt = f"""
You are a financial analyst. Use only the summarized evidence.

QUESTION:
{query}

EVIDENCE:
{context_text}

Write a structured, factual comparison.
"""

        return self.llm.generate(prompt)
