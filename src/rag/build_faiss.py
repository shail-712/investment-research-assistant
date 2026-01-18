import faiss
import numpy as np
import os

def build_faiss_index():
    embeddings_path = "data/processed/embeddings.npy"
    index_path = "data/processed/faiss_index.bin"

    # --- Check files exist ---
    if not os.path.exists(embeddings_path):
        raise FileNotFoundError("Embeddings not found. Run build_embeddings.py first.")

    print("Loading embeddings...")
    embeddings = np.load(embeddings_path)

    # --- Check dimensions ---
    if len(embeddings.shape) != 2:
        raise ValueError("Embeddings should be a 2D array of shape (N, dim).")

    num_vectors, dim = embeddings.shape
    print(f"Embedding count: {num_vectors}")
    print(f"Embedding dimension: {dim}")

    # --- Create FAISS index ---
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # --- Save index ---
    faiss.write_index(index, index_path)

    print("FAISS index created and saved successfully!")


if __name__ == "__main__":
    build_faiss_index()
