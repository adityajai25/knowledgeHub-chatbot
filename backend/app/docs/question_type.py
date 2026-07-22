import re
from typing import Literal

QuestionType = Literal[
    "WHO",
    "WHAT",
    "WHY",
    "WHEN",
    "WHERE",
    "HOW",
    "SUMMARY",
    "COMPARISON",
    "RECOMMENDATION",
    "PROCEDURE",
    "GENERAL",
]

# Keeps question classification logic centralized for cleaner prompt selection.
def detect_question_type(query: str) -> QuestionType:
    q = (query or "").strip().lower()
    if not q:
        return "GENERAL"

    if re.search(r"\b(summary|summarize|overview|gist|main idea|key points|briefly describe)\b", q):
        return "SUMMARY"
    if re.search(r"\b(compare|comparison|vs\b|difference|differences|similarities)\b", q):
        return "COMPARISON"
    if re.search(r"\b(recommend|should i|advise|suggest|best approach|what is the best)\b", q):
        return "RECOMMENDATION"
    if re.search(r"\b(procedure|process|steps|how to|guide|method)\b", q):
        return "PROCEDURE"
    if q.startswith("who") or re.search(r"\bwho\b", q[:10]):
        return "WHO"
    if q.startswith("what") or re.search(r"\bwhat\b", q[:10]):
        return "WHAT"
    if q.startswith("why") or re.search(r"\bwhy\b", q[:10]):
        return "WHY"
    if q.startswith("when") or re.search(r"\bwhen\b", q[:10]):
        return "WHEN"
    if q.startswith("where") or re.search(r"\bwhere\b", q[:10]):
        return "WHERE"
    if q.startswith("how") or re.search(r"\bhow\b", q[:10]):
        return "HOW"
    return "GENERAL"
