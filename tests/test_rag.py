from src.agent.rag_engine import RAGEngine

rag = RAGEngine()

response = rag.answer(
    "Compare NVIDIA, AMD, and Intel AI chip business performance in 2025."
)

print(response)



