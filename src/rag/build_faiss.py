"""
Build the FAISS index from precomputed embeddings and (optionally) upload it to S3.

This closes the gap between the local RAG artifacts (data/processed/) and the
deployed RetrieverLambda, which downloads the following keys from S3 at runtime:
    - faiss_index.bin   (the FAISS vector index)
    - metadata.json     (chunk metadata, indexed by vector position)

Usage:
    # 1. Build the index locally only (no AWS credentials needed):
    python src/rag/build_faiss.py

    # 2. Build and run a quick self-test search to confirm it works:
    python src/rag/build_faiss.py --test

    # 3. Build and upload to S3 (requires valid AWS credentials):
    python src/rag/build_faiss.py --upload --bucket investment-research-kb-shail
"""

import argparse
import os

import faiss
import numpy as np

# ─── Paths and S3 keys ───────────────────────────────────────────────────────
PROCESSED_DIR = os.path.join("data", "processed")
EMBEDDINGS_PATH = os.path.join(PROCESSED_DIR, "embeddings.npy")
METADATA_PATH = os.path.join(PROCESSED_DIR, "metadata.json")
INDEX_PATH = os.path.join(PROCESSED_DIR, "faiss_index.bin")

# These MUST match the keys RetrieverLambda downloads (see lambdas/retriever/lambda_function.py)
S3_INDEX_KEY = "faiss_index.bin"
S3_META_KEY = "metadata.json"
DEFAULT_BUCKET = os.environ.get("S3_BUCKET", "investment-research-kb-shail")


def build_index() -> faiss.Index:
    """Load embeddings and build a FAISS L2 index. Returns the built index."""
    if not os.path.exists(EMBEDDINGS_PATH):
        raise FileNotFoundError(
            f"Embeddings not found at {EMBEDDINGS_PATH}. Run build_embeddings.py first."
        )
    if not os.path.exists(METADATA_PATH):
        raise FileNotFoundError(
            f"Metadata not found at {METADATA_PATH}. Run build_chunks.py first."
        )

    print("Loading embeddings...")
    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")

    if embeddings.ndim != 2:
        raise ValueError("Embeddings should be a 2D array of shape (N, dim).")

    num_vectors, dim = embeddings.shape
    print(f"  Embedding count:     {num_vectors}")
    print(f"  Embedding dimension: {dim}")

    # IndexFlatL2 matches the L2 search used by the retriever lambda.
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)
    print(f"FAISS index built and saved to {INDEX_PATH} ({index.ntotal} vectors).")
    return index


def upload_to_s3(bucket: str) -> None:
    """Upload the FAISS index and metadata to S3 under the keys the lambda expects."""
    import boto3  # imported here so local-only builds don't require boto3/creds

    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"{INDEX_PATH} not found. Build the index first.")

    s3 = boto3.client("s3")
    print(f"Uploading to s3://{bucket}/ ...")
    s3.upload_file(INDEX_PATH, bucket, S3_INDEX_KEY)
    print(f"  uploaded {INDEX_PATH} -> s3://{bucket}/{S3_INDEX_KEY}")
    s3.upload_file(METADATA_PATH, bucket, S3_META_KEY)
    print(f"  uploaded {METADATA_PATH} -> s3://{bucket}/{S3_META_KEY}")
    print("Upload complete.")


def self_test(index: faiss.Index) -> None:
    """Run a sample search against the freshly built index to prove it works."""
    import json

    with open(METADATA_PATH, encoding="utf-8") as f:
        metadata = json.load(f)

    if index.ntotal != len(metadata):
        raise ValueError(
            f"Vector count ({index.ntotal}) != metadata rows ({len(metadata)}). "
            "The index and metadata are out of sync."
        )

    # Use the first stored vector as a query so we don't need the Gemini API here.
    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")
    query_vec = embeddings[:1]
    distances, ids = index.search(query_vec, 3)

    print("\nSelf-test search (top 3 for the first stored chunk):")
    for rank, (i, dist) in enumerate(zip(ids[0], distances[0]), 1):
        meta = metadata[i]
        preview = meta.get("text", "")[:80].replace("\n", " ")
        print(f"  {rank}. [{meta.get('company')} | {meta.get('filename')}] d={dist:.3f} :: {preview}...")
    print("Self-test passed: index and metadata are aligned.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and optionally upload the FAISS index.")
    parser.add_argument("--upload", action="store_true", help="Upload index + metadata to S3.")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="Target S3 bucket name.")
    parser.add_argument("--test", action="store_true", help="Run a self-test search after building.")
    args = parser.parse_args()

    index = build_index()

    if args.test:
        self_test(index)

    if args.upload:
        upload_to_s3(args.bucket)
    else:
        print("Local build only. Re-run with --upload to push to S3.")


if __name__ == "__main__":
    main()
