import re


def is_greeting(query: str) -> bool:
    text = (query or "").strip().lower()
    if not text:
        return False
    greeting_patterns = [
        r"^(hi|hello|hey|good morning|good afternoon|good evening|good day|how are you|how are you doing)[.!?,]*$",
        r"^(hi|hello|hey|good morning|good afternoon|good evening|good day|how are you|how are you doing)\s+.*$",
    ]
    return any(re.fullmatch(pattern, text) for pattern in greeting_patterns)


def trim_answer(text: str, max_words: int = 100) -> str:
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    trimmed = " ".join(words[:max_words]).strip()
    return trimmed + "..."


def is_absent_answer(text: str) -> bool:
    if not text:
        return False
    normalized = text.lower()
    absent_phrases = [
        "i don’t have enough information from the uploaded files to answer that question",
        "i don't have enough information from the uploaded files to answer that question",
        "the uploaded documents do not contain this information",
        "there is not enough information in the uploaded files",
        "not enough information",
    ]
    return any(phrase in normalized for phrase in absent_phrases)


def build_absent_response() -> str:
    return "I don’t have enough information from the uploaded files to answer that question."


def sanitize_answer(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Remove an echoed user question prefix when the model repeats the query.
    if cleaned.startswith("User Question:"):
        match = re.match(r"^User Question:.*?[\?\!\.](?:\s*)", cleaned, flags=re.DOTALL)
        if match:
            cleaned = cleaned[match.end():].strip()
        else:
            cleaned = re.sub(r"^User Question:[^\n]*(?:\n+|\s*)", "", cleaned, flags=re.DOTALL).strip()

    # Normalize repeated blank lines and preserve headings.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Strip out explicit sources or confidence feedback from model output.
    cleaned = re.split(r"\nSources?:", cleaned, maxsplit=1)[0].strip()
    cleaned = re.sub(r"(?i)\bConfidence:\s*.*", "", cleaned).strip()
    return cleaned.strip()
