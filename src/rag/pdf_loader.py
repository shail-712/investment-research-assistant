import os
import pdfplumber
import re

# ---------- 1. CLEANING UTILITIES ----------

def remove_headers_footers(text: str) -> str:
    """
    Removes repeating headers/footers often found in SEC filings,
    press releases, and investor PDFs.
    """
    if not text:
        return ""

    # Remove page numbers
    text = re.sub(r"Page\s*\d+\s*of\s*\d+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*\d+\s*$", " ", text, flags=re.MULTILINE)

    # Remove common header/footer patterns
    patterns = [
        r"NVIDIA Corporation.*Quarterly.*", 
        r"Advanced Micro Devices.*", 
        r"Intel Corporation.*",
        r"Unaudited Condensed.*", 
        r"Consolidated Statements.*"
    ]

    for p in patterns:
        text = re.sub(p, " ", text, flags=re.IGNORECASE)

    return text


def fix_line_breaks(text: str) -> str:
    """
    Fix unstable line breaks that break sentences in PDFs.
    """
    # Fix hyphenated line breaks
    text = text.replace("-\n", "")

    # Replace single newlines (broken sentences) with spaces
    text = re.sub(r"(?<!\.)\n(?!\n)", " ", text)

    # Reduce multiple newlines to a single separator
    text = re.sub(r"\n{2,}", "\n", text)

    return text


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_tables(page) -> str:
    """
    Flatten tables into readable text.
    """
    table_text = ""
    try:
        tables = page.extract_tables()
        if tables:
            for table in tables:
                for row in table:
                    row = [cell if cell else "" for cell in row]
                    table_text += " | ".join(row) + "\n"
    except:
        pass
    return table_text


# ---------- 2. CORE EXTRACTION ----------

def extract_page_text(page) -> str:
    """
    Best-effort extraction:
    - First try layout-aware extraction
    - Fall back to standard extraction
    - Append cleaned table text
    """
    text = page.extract_text(layout=True) or page.extract_text() or ""
    tables = extract_tables(page)

    combined = text + "\n" + tables
    return combined


def extract_text_robust(pdf_path: str) -> str:
    """
    Completely improved text extraction for financial documents.
    """
    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = extract_page_text(page)

            # Apply cleaning pipeline
            page_text = remove_headers_footers(page_text)
            page_text = fix_line_breaks(page_text)
            page_text = normalize_whitespace(page_text)

            if page_text:
                full_text += page_text + "\n\n"

    return full_text.strip()


# ---------- 3. LOAD ALL PDFs ----------

def load_all_pdfs(folder_path: str):
    documents = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            print(f"Extracting {filename}...")

            text = extract_text_robust(file_path)

            documents.append({
                "filename": filename,
                "text": text
            })

    return documents
