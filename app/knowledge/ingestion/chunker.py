"""
Simple, dependency-free word-based chunker. Splits on paragraph boundaries
first (to avoid cutting sentences awkwardly where possible), then falls back
to a sliding window with overlap for long paragraphs. Good enough for policy
articles / FAQs; swap for a tokenizer-aware splitter if you later ingest
long-form documents where token-exact limits matter.
"""
import re

from app.core.config import get_settings


def normalize_query(text: str) -> str:
    """Query normalization used at retrieval time: collapse whitespace,
    strip, and lightly normalize punctuation. Kept separate from chunking
    normalization since queries are short and shouldn't be paragraph-split."""
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, *, chunk_size_words: int | None = None, overlap_words: int | None = None) -> list[str]:
    settings = get_settings()
    chunk_size_words = chunk_size_words or settings.embedding_chunk_size_words
    overlap_words = overlap_words or settings.embedding_chunk_overlap_words

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current_words: list[str] = []

    for paragraph in paragraphs:
        para_words = paragraph.split()

        if len(current_words) + len(para_words) <= chunk_size_words:
            current_words.extend(para_words)
            continue

        if current_words:
            chunks.append(" ".join(current_words))
            # carry the overlap tail forward into the next chunk for context continuity
            current_words = current_words[-overlap_words:] if overlap_words else []

        if len(para_words) > chunk_size_words:
            # paragraph itself exceeds the limit -- slide a window over it
            start = 0
            while start < len(para_words):
                end = start + chunk_size_words
                chunks.append(" ".join(para_words[start:end]))
                start = end - overlap_words if overlap_words else end
            current_words = []
        else:
            current_words.extend(para_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks