import json
from rag.pdf_loader import load_all_pdfs
from rag.text_cleaner import clean_text
from rag.chunker import chunk_text

def build_chunks():
    docs = load_all_pdfs("data/raw/")
    all_chunks = []

    for d in docs:
        print(f"Chunking {d['filename']}...")

        clean = clean_text(d["text"])
        chunks = chunk_text(clean, max_tokens=300, overlap=50)

        # Attach metadata
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{d['filename']}_{i}",
                "filename": d["filename"],
                "text": chunk
            })

        print(f" → Created {len(chunks)} chunks")

    print(f"Total chunks created: {len(all_chunks)}")

    # --- Save BEFORE returning ---
    with open("data/processed/chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)
    
    return all_chunks

if __name__ == "__main__":
    build_chunks()