#generate embeddings using Google Gemini API

from google.genai import Client
from dotenv import load_dotenv
import os
import numpy as np

class EmbeddingService:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY missing")

        self.client = Client(api_key=api_key)
        self.model = "models/text-embedding-004" 

    def embed(self, text: str) -> np.ndarray:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text
        )
        
        emb = np.array(response.embeddings[0].values, dtype="float32")
        return emb