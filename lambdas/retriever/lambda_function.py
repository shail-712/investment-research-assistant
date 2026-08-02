import json
import os
import boto3
import faiss
import numpy as np
from embedding_service import EmbeddingService

S3_BUCKET = os.environ["S3_BUCKET"]
INDEX_KEY = "faiss_index.bin"
META_KEY = "metadata.json"

s3 = boto3.client("s3")

index = None
metadata = None
embedder = EmbeddingService()

def load_index():
    global index, metadata
    if index is None:
        s3.download_file(S3_BUCKET, INDEX_KEY, "/tmp/index.bin")
        s3.download_file(S3_BUCKET, META_KEY, "/tmp/meta.json")
        index = faiss.read_index("/tmp/index.bin")
        with open("/tmp/meta.json") as f:
            metadata = json.load(f)

def lambda_handler(event, context):
    query = event.get("query")
    if not query:
        return {"statusCode": 400, "body": "Missing query"}

    load_index()

    q_vec = np.array([embedder.embed(query)], dtype="float32")
    _, ids = index.search(q_vec, 5)

    results = [metadata[i] for i in ids[0]]

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }
