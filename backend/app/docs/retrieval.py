from typing import Any, Dict, List

from app.embeddings.hf_client import get_hf_client
from app.core.config import settings

# Retrieval helper encapsulates embedding generation, filtering, and chunk selection.

def select_top_chunks(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    hf = get_hf_client()
    qvec = hf.embed_text(query)
    hits = hf.search(qvec, top_k=top_k)
    return _clean_hits(hits)


def _clean_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_text = set()
    unique_hits: List[Dict[str, Any]] = []

    # Remove exact duplicate chunks and preserve ranking.
    for hit in hits:
        meta = hit.get("meta") or {}
        text = (meta.get("text") or "").strip()
        if not text:
            continue
        if text in seen_text:
            continue
        seen_text.add(text)
        unique_hits.append(hit)

    # If multiple chunks come from the same document, merge adjacent chunks into a single context block.
    return _merge_related_chunks(unique_hits)


def _merge_related_chunks(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = {}
    for hit in hits:
        meta = hit.get("meta") or {}
        filename = meta.get("filename") or "document"
        doc_group = grouped.setdefault(filename, [])
        doc_group.append(hit)

    merged: List[Dict[str, Any]] = []
    for filename, group in grouped.items():
        group.sort(key=lambda item: (item.get("meta", {}).get("chunk_index") or 0))
        if len(group) <= 1:
            merged.extend(group)
            continue

        combined_text = []
        base_hit = group[0].copy()
        for hit in group:
            text = (hit.get("meta", {}).get("text") or "").strip()
            if text:
                combined_text.append(text)
        base_hit["meta"]["text"] = " \n\n".join(combined_text)
        merged.append(base_hit)

    # Preserve the original sort order by score where possible.
    merged.sort(key=lambda h: h.get("meta", {}).get("chunk_index", 0))
    return merged[: settings.retrieval_top_k]
