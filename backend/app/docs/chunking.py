from typing import List


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
    if not text:
        return []

    text = text.strip()
    if not text:
        return []

    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size

    chunks: List[str] = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks
