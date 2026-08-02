"""
Embedding service for the RetrieverLambda.

Generates a query embedding using Google's text-embedding-004 model (768-dim),
matching the embeddings that were used to build the FAISS index.

The Gemini API key is read from the GEMINI_API_KEY environment variable, which
is injected by the SAM template (resolved from SSM Parameter Store).
"""

import os

import numpy as np
from google.genai import Client

MODEL = "models/text-embedding-004"


class EmbeddingService:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        self.client = Client(api_key=api_key)
        self.model = MODEL

    def embed(self, text: str) -> np.ndarray:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return np.array(response.embeddings[0].values, dtype="float32")
