from typing import Any, Dict, List, Tuple

# Deduplicate sources by document and chunk identity so the same document doesn't appear multiple times.
# This reduces duplicate citations and improves source quality.

def deduplicate_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[Any, Any, Any]] = set()
    unique: List[Dict[str, Any]] = []
    for source in sources:
        meta = source.get("meta", {}) if isinstance(source, dict) else {}
        doc_id = meta.get("doc_id")
        filename = meta.get("filename")
        chunk_index = meta.get("chunk_index")
        key = (doc_id, filename, chunk_index)
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def build_source_label(source: Dict[str, Any]) -> str:
    meta = source.get("meta", {}) if isinstance(source, dict) else {}
    filename = meta.get("filename") or "Document"
    chunk_index = meta.get("chunk_index")
    if chunk_index is not None:
        return f"{filename} (chunk {chunk_index})"
    return filename


def format_source_excerpt(source: Dict[str, Any]) -> str:
    meta = source.get("meta", {}) if isinstance(source, dict) else {}
    text = meta.get("text", "") or ""
    snippet = text.strip()
    if len(snippet) > 180:
        snippet = snippet[:177].rsplit(" ", 1)[0] + "..."
    return snippet


def extract_source_documents(sources: List[Dict[str, Any]]) -> List[str]:
    labels = []
    seen = set()
    for source in sources:
        label = build_source_label(source)
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels
