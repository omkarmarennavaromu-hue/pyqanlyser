import re
import pdfplumber


def extract_text(pdf_path: str) -> str:
    """
    Extract and clean text from a multi-page PDF file.
    Returns a single cleaned string.
    """

    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                page_text = page.extract_text()

                # fallback safety
                if page_text:
                    pages_text.append(page_text)
                else:
                    pages_text.append("")

            except Exception:
                # skip broken pages safely
                continue

    raw = "\n".join(pages_text).strip()

    if not raw:
        return ""

    return _clean_text(raw)


def _clean_text(text: str) -> str:
    """
    Clean extracted PDF text:
    - Remove junk characters
    - Normalize spacing
    - Remove separators
    """

    # Remove weird non-printable characters
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]", " ", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix spacing
    text = re.sub(r"[ \t]+", " ", text)

    # Remove separator lines
    text = re.sub(r"^\s*[-_=.]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Reduce large blank spaces
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
