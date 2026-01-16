#build FAISS index for RAG system using saved embeddings 

import faiss
import numpy as np
import json

def build_faiss_index():
    print("Loading embeddings...")

    embeddings = np.load("data/processed/embeddings.npy")

    dim = embeddings.shape[1]
    print(f"Embedding dimension: {dim}")

    index = faiss.IndexFlatL2(dim)  # L2 distance index
    index.add(embeddings)

    faiss.write_index(index, "data/processed/faiss_index.bin")

    print("FAISS index created and saved!")


if __name__ == "__main__":
    build_faiss_index()
