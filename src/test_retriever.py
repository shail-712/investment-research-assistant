from src.rag.faiss_retriever import retrieve_chunks

results = retrieve_chunks("What did NVIDIA report about data center revenue?")
for r in results:
    print("\n---- Result ----")
    print("File:", r["filename"])
    print("Text:", r["text"][:300])
