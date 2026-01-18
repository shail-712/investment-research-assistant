import json
from rag.pdf_loader import load_all_pdfs
from rag.text_cleaner import clean_text
from rag.chunker import chunk_text

def build_chunks():
    docs = load_all_pdfs("data/raw/")
    all_chunks = []

    for d in docs:
        print(f"Chunking {d['filename']}...")

        # Determine company PER DOCUMENT
        company = (
            "NVIDIA" if "NVIDIA" in d["filename"] else
            "AMD" if "AMD" in d["filename"] else
            "Intel" if "Intel" in d["filename"] else
            "Unknown"
        )

        clean = clean_text(d["text"])
        chunks = chunk_text(clean, max_tokens=300, overlap=50)

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{d['filename']}_{i}",
                "filename": d["filename"],
                "company": company,
                "text": chunk
            })

        print(f" → Created {len(chunks)} chunks")

    print(f"Total chunks: {len(all_chunks)}")

    with open("data/processed/chunks.json", "w") as f:
        json.dump(all_chunks, f, indent=2)

    return all_chunks



if __name__ == "__main__":
    build_chunks()