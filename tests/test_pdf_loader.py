from src.rag.pdf_loader import load_all_pdfs
from src.rag.text_cleaner import clean_text

docs = load_all_pdfs("data/raw/")
print(f"Loaded {len(docs)} documents")

for d in docs:
    print("----", d["filename"], "----")
    print(clean_text(d["text"])[:1000])
