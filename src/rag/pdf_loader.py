import os
from pypdf import PdfReader

def load_pdf_text(file_path: str) -> str:
    """
    Extracts all text from a PDF file.
    """
    reader = PdfReader(file_path)
    full_text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + "\n"

    return full_text


def load_all_pdfs(folder_path: str):
    """
    Loads and extracts text from all PDFs in data/raw/.
    """
    documents = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            text = load_pdf_text(file_path)

            documents.append({
                "filename": filename,
                "text": text
            })

    return documents
