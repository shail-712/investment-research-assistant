# compressor module to summarize text chunks using LLM service  

from src.agent.llm_service import LLMService

class Compressor:
    def __init__(self):
        self.llm = LLMService()

    def compress(self, chunk_text: str):
        prompt = f"""
Summarize the following financial text into 2–3 sentences.
Make it concise, factual, and preserve numbers:

TEXT:
{chunk_text}
"""
        return self.llm.generate(prompt)
