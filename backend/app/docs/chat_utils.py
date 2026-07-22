from typing import List, Dict, Any


def is_summary_query(query: str) -> bool:
    if not query:
        return False
    lower = query.lower()
    summary_keywords = [
        "summarize",
        "summarise",
        "summary",
        "overview",
        "gist",
        "main idea",
        "key points",
        "recap",
        "briefly describe",
        "what is the document about",
        "high-level",
    ]
    return any(keyword in lower for keyword in summary_keywords)


def format_context(hits: List[Dict[str, Any]]) -> List[str]:
    formatted = []
    for hit in hits:
        meta = hit.get("meta") or {}
        text = meta.get("text", "")
        if not text:
            continue

        # Keep each context item reasonably short so the prompt stays manageable.
        snippet = text if len(text) <= 800 else text[:800].rsplit(" ", 1)[0] + "..."
        formatted.append(snippet)
    return formatted


def build_rag_prompt(system_prompt: str, history_context: str, query: str, context_texts: List[str]) -> str:
    prompt = system_prompt
    if history_context:
        prompt += history_context

    prompt += f"User Question: {query}\n\n"

    if context_texts:
        prompt += "Use the following relevant document excerpts only when they directly answer the question:\n"
        for i, context in enumerate(context_texts, start=1):
            prompt += f"Excerpt {i}: {context}\n"
        prompt += "\n"
    else:
        prompt += (
            "There are no relevant document excerpts available for this question. "
            "Do not hallucinate. If the documents do not answer the question, say: "
            "'I don’t have enough information from the uploaded files to answer that question.'\n\n"
        )

    prompt += (
        "Answer in fewer than 100 words. Be direct, practical, and avoid unrelated details. "
        "Structure your answer exactly with the following headings: Root Cause, Evidence, Recommendation, AI Insights, Sources. "
        "If a heading does not apply, include it with a short note such as 'Not enough information'. "
        "Use the document excerpts only when they directly answer the question. Always cite file names in the Sources section, and do not invent content."
    )
    return prompt


def build_summary_prompt(system_prompt: str, history_context: str, query: str, context_texts: List[str]) -> str:
    prompt = system_prompt
    if history_context:
        prompt += history_context

    prompt += f"User Question: {query}\n\n"
    prompt += "Provide a concise document overview while keeping the answer structured and grounded in the uploaded files. "
    prompt += "Do not invent content. Use headings: Root Cause, Evidence, Recommendation, AI Insights, Sources. "

    if context_texts:
        prompt += "Use these relevant excerpts from the uploaded files:\n"
        for i, context in enumerate(context_texts, start=1):
            prompt += f"Excerpt {i}: {context}\n"
        prompt += "\n"
    else:
        prompt += (
            "There are no relevant document excerpts available for this question. "
            "Do not hallucinate. If the documents do not answer the question, say: "
            "'I don’t have enough information from the uploaded files to answer that question.'\n\n"
        )

    prompt += (
        "If you can answer using the document excerpts, do so clearly and cite the source file names. "
        "Focus on the most important themes and avoid listing every excerpt."
    )
    return prompt
