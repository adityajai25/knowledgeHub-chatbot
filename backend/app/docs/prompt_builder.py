from typing import List
from app.docs.question_type import QuestionType

SYSTEM_PROMPT = (
    "You are a professional document intelligence assistant. Answer only from the retrieved document excerpts below. "
    "Do not invent facts, do not guess, and do not include information that is not present in the excerpts. "
    "Do not mention chunk labels, excerpt IDs, or source metadata in the final answer. "
    "If the evidence does not support an answer, say exactly:\n"
    "I don’t have enough information from the uploaded files to answer that question.\n"
    "Do not include any explicit source list in the final answer. "
    "Keep the response concise, structured, and professional. Quote evidence only when it is directly relevant. "
    "If the retrieved excerpts disagree, describe the conflict clearly and do not choose a fabricated resolution."
)

QUESTION_TEMPLATES = {
    "WHO": (
        "Answer:\nProvide a direct response to the person or role identified by the documents.\n"
        "Evidence:\nList the most relevant excerpted phrases.\n"
    ),
    "WHAT": (
        "Answer:\nExplain the concept, item, or status referenced by the question.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "WHY": (
        "Root Cause:\nExplain why this happened based on the documents.\n"
        "Evidence:\nCite the most relevant excerpts.\n"
        "Recommendations:\nInclude a recommendation only if the documents support one.\n"
    ),
    "WHEN": (
        "Answer:\nState the timing or conditions when this is true.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "WHERE": (
        "Answer:\nState the location or context based on the documents.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "HOW": (
        "Answer:\nExplain the process or method described by the documents.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "SUMMARY": (
        "Summary:\nProvide a concise overview of the information in the retrieved excerpts.\n"
        "Key Findings:\nList the most important points.\n"
    ),
    "COMPARISON": (
        "Answer:\nCompare the items or options by describing differences and similarities with evidence.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "RECOMMENDATION": (
        "Answer:\nOffer the recommendation supported by the documents only if it is explicitly present.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "PROCEDURE": (
        "Steps:\nList the procedural steps described in the documents.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
    "GENERAL": (
        "Answer:\nProvide a clear response based on the retrieved excerpts.\n"
        "Evidence:\nCite the relevant excerpts.\n"
    ),
}


def build_prompt(query: str, question_type: QuestionType, context_texts: List[str]) -> str:
    template = QUESTION_TEMPLATES.get(question_type, QUESTION_TEMPLATES["GENERAL"])
    prompt = SYSTEM_PROMPT + "\n\n"
    prompt += f"Question Type: {question_type}\n"
    prompt += f"Question: {query.strip()}\n\n"
    prompt += (
        "Use only the text below. Do not insert or repeat any metadata such as chunk numbers, excerpt labels, or source filenames in your answer. "
        "If the evidence does not clearly answer the question, reply with: I don’t have enough information from the uploaded files to answer that question.\n\n"
    )
    if context_texts:
        prompt += "Retrieved excerpts:\n"
        for idx, excerpt in enumerate(context_texts, start=1):
            prompt += f"Excerpt {idx}: \"{excerpt}\"\n"
    else:
        prompt += "Retrieved excerpts: none\n"
    prompt += "\n" + template
    return prompt
