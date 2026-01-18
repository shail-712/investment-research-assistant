# faiss retriever for RAG system
import faiss
import numpy as np
import json
from src.rag.embedding_service import EmbeddingService
import os
index_path = "data/processed/faiss_index.bin"
metadata_path = "data/processed/metadata.json"
class MultiCompanyRetriever:
    def __init__(self):
        if not os.path.exists(index_path):
            raise FileNotFoundError("FAISS index not found. Run build_faiss.py first.")

        if not os.path.exists(metadata_path):
            raise FileNotFoundError("Metadata not found. Run build_embeddings.py first.")

        self.index = faiss.read_index(index_path)
        with open(metadata_path, "r") as f:
            self.metadata = json.load(f)
        self.embedder = EmbeddingService()

    def query(self, text: str, per_company_k=3):
        query_vec = self.embedder.embed(text).reshape(1, -1)

        # Global top K large number so we can filter
        distances, indices = self.index.search(query_vec, 50)

        hits = [self.metadata[i] for i in indices[0] if i < len(self.metadata)]

        # group by company
        groups = {"NVIDIA": [], "AMD": [], "Intel": []}
        for h in hits:
            company = h.get("company", "Unknown")
            if company in groups:
                groups[company].append(h)

        # take top per company
        results = []
        for c in ["NVIDIA", "AMD", "Intel"]:
            results.extend(groups[c][:per_company_k])

        return results


def retrieve_chunks(query: str, k=3):
    return MultiCompanyRetriever().query(query, per_company_k=k)
