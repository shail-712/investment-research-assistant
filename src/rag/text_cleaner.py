import re

def clean_text(text: str) -> str:
    """
    Clean noisy characters, extra whitespace, and line breaks.
    """
    # Remove excessive newlines
    text = re.sub(r'\n+', '\n', text)

    # Remove weird unicode characters
    text = text.replace("\x00", " ")

    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()
