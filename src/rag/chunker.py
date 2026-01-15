import re

def split_into_sentences(text: str):
    """
    Splits text into sentences using regex.
    More reliable than splitting only on periods.
    """
    sentence_endings = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_endings, text)
    return [s.strip() for s in sentences if len(s.strip()) > 0]


def chunk_text(text: str, max_tokens: int = 300, overlap: int = 50):
    """
    Chunk text into overlapping segments.
    
    max_tokens = approximate number of tokens per chunk.
    overlap    = approximate overlap size to preserve context.
    """
    sentences = split_into_sentences(text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence.split())

        # If adding this sentence exceeds max_tokens, finalize chunk
        if current_length + sentence_len > max_tokens:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)

            # Start new chunk with overlap
            overlap_words = " ".join(current_chunk[-overlap:])
            current_chunk = overlap_words.split()
            current_length = len(current_chunk)

        # Add sentence to current chunk
        current_chunk.append(sentence)
        current_length += sentence_len

    # Add final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks


