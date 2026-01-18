import json
import numpy as np
import os

from src.rag.embedding_service import EmbeddingService   # FIXED IMPORT

def build_embeddings():
    with open("data/processed/chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    embedder = EmbeddingService()

    embeddings = []
    metadata = []

    print("Generating embeddings...")

    for chunk in chunks:
        emb = embedder.embed(chunk["text"])
        embeddings.append(emb)

        # IMPORTANT: include the company field
        metadata.append({
            "id": chunk["id"],
            "filename": chunk["filename"],
            "company": chunk["company"],   # <-- FIX
            "text": chunk["text"]
        })

    embeddings = np.array(embeddings, dtype="float32")

    np.save("data/processed/embeddings.npy", embeddings)

    with open("data/processed/metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Embedding generation complete!")
    print(f"Total embeddings: {len(embeddings)}")


if __name__ == "__main__":
    build_embeddings()
