# faiss retriever for RAG system

import faiss
import numpy as np
import json
import os

from src.rag.embedding_service import EmbeddingService

class FAISSRetriever:
    def __init__(self, index_path="data/processed/faiss_index.bin", metadata_path="data/processed/metadata.json"):
        if not os.path.exists(index_path):
            raise FileNotFoundError("FAISS index not found. Run build_faiss.py first.")

        if not os.path.exists(metadata_path):
            raise FileNotFoundError("Metadata not found. Run build_embeddings.py first.")

        self.index = faiss.read_index(index_path)

        with open(metadata_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        self.embedder = EmbeddingService()

    def query(self, text: str, top_k: int = 5):
        query_vector = self.embedder.embed(text).reshape(1, -1)

        distances, indices = self.index.search(query_vector, top_k)

        results = []
        for idx in indices[0]:
            if idx < len(self.metadata):
                results.append(self.metadata[idx])

        return results


# Convenience function (used by API)
def retrieve_chunks(query: str, k: int = 5):
    retriever = FAISSRetriever()
    return retriever.query(query, top_k=k)
