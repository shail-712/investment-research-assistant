from src.rag.faiss_retriever import retrieve_chunks

query = (
    "Give me a competitive comparison between NVIDIA, AMD, and Intel in GPU/AI chips. "
    "Top companies, market share, recent developments, and future outlook."
)

results = retrieve_chunks(query)

print(f"Results found: {len(results)}")

for r in results:
    print("\n---- Result ----")
    print("File:", r["filename"])
    print("Company:", r["company"])
    print("Text:", r["text"][:300])
