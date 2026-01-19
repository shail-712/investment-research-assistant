import faiss
import numpy as np
import json

class CloudRetriever:
    def __init__(self, artifact_dir="aws_artifacts/"):
        self.index = faiss.read_index(f"{artifact_dir}/faiss_index.bin")
        self.metadata = json.load(open(f"{artifact_dir}/metadata.json"))
        self.embeddings_dim = self.index.d

    def embed(self, text: str):
        # Use your existing EmbeddingService
        from src.agent.llm_service import EmbeddingService
        embedder = EmbeddingService()
        return embedder.embed(text)

    def search(self, query: str, top_k=5):
        vec = np.array(self.embed(query)).reshape(1, -1)
        distances, indices = self.index.search(vec, top_k)

        results = []
        for idx in indices[0]:
            results.append(self.metadata[idx])

        return results
