import asyncio
import io
import json
import os
import re
from typing import List, Optional

import requests as req_lib  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.embeddings.hf_client import get_hf_client
from app.models import ChatMessage, ChatSession, Document
from PyPDF2 import PdfReader

router = APIRouter()

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "uploads")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Industrial System Prompt (shared across all chat endpoints)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a Senior Industrial Engineer and Troubleshooting Specialist. "
    "Your job is to analyze industrial documents (machine manuals, failure reports, "
    "SOPs, maintenance logs) and provide DETAILED, ACTIONABLE guidance.\n\n"
    "When answering:\n"
    "1. **Identify the Problem**: Clearly state what issue or failure is described.\n"
    "2. **Root Cause Analysis**: Explain the likely root causes based on the document.\n"
    "3. **Step-by-Step Fix**: Provide a numbered procedure to resolve the issue.\n"
    "4. **Safety Precautions**: Mention any safety warnings or precautions.\n"
    "5. **Preventive Measures**: Suggest how to prevent recurrence.\n"
    "6. **Cite Sources**: Reference which document sections your answer comes from.\n\n"
    "Be thorough and detailed. Do NOT give short or vague answers. "
    "If the documents don't contain enough info, say so clearly and suggest what to look for.\n\n"
)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ").replace("\x0c", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages).strip()
        if text:
            return normalize_text(text)
    except Exception:
        pass

    try:
        from pdf2image import convert_from_bytes
        from pytesseract import image_to_string

        images = convert_from_bytes(content)
        texts: List[str] = [str(image_to_string(img)) for img in images]
        text = "\n".join(texts).strip()
        if text:
            return normalize_text(text)
    except Exception:
        pass

    return ""


# ---------------------------------------------------------------------------
# LLM abstraction: Ollama / HuggingFace / local pipeline
# ---------------------------------------------------------------------------

def call_ollama(prompt: str) -> Optional[str]:
    """Call the local Ollama REST API."""
    try:
        url = f"{settings.ollama_base_url}/api/generate"
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": settings.max_new_tokens,
                "temperature": settings.llm_temperature,
            },
        }
        resp = req_lib.post(url, json=payload, timeout=settings.ollama_timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        print(f"Ollama error: {e}")
        return None


def call_hf_api(prompt: str) -> Optional[str]:
    """Call the HuggingFace Inference API."""
    if not (settings.hf_api_key or settings.hf_inference_endpoint):
        return None
    try:
        url = (
            settings.hf_inference_endpoint
            or f"https://api-inference.huggingface.co/models/{settings.hf_generation_model}"
        )
        headers = {"Authorization": f"Bearer {settings.hf_api_key}"} if settings.hf_api_key else {}
        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": settings.max_new_tokens,
                "temperature": settings.llm_temperature,
                "return_full_text": False,
            },
        }
        resp = req_lib.post(url, headers=headers, json=data, timeout=settings.ollama_timeout)
        resp.raise_for_status()
        gen = resp.json()
        if isinstance(gen, list) and gen and "generated_text" in gen[0]:
            return gen[0]["generated_text"].strip()
        if isinstance(gen, dict) and "generated_text" in gen:
            return gen["generated_text"].strip()
    except Exception as e:
        print(f"HF API error: {e}")
    return None


def call_local_pipeline(prompt: str) -> Optional[str]:
    """Fallback: run a local transformers pipeline."""
    try:
        from transformers import pipeline
        gen_pipe = pipeline(task=None, model=settings.hf_generation_model)  # type: ignore[arg-type]
        out = gen_pipe(prompt, max_new_tokens=settings.max_new_tokens)
        if isinstance(out, list) and out and "generated_text" in out[0]:
            return out[0]["generated_text"].strip()
    except Exception:
        pass
    return None


def call_llm(prompt: str) -> Optional[str]:
    """Route to the configured LLM provider. Falls back through the chain."""
    if settings.llm_provider == "ollama":
        result = call_ollama(prompt)
        if result:
            return result
        # Fallback to HF if Ollama fails
        result = call_hf_api(prompt)
        if result:
            return result
    else:
        # HuggingFace provider
        result = call_hf_api(prompt)
        if result:
            return result
        # Fallback to local pipeline
        result = call_local_pipeline(prompt)
        if result:
            return result

    return None


def generate_summary(text: str) -> str:
    """Generate a 3-5 sentence summary using configured LLM provider."""
    snippet = text[:settings.summary_snippet_length]
    prompt = (
        f"Summarize the following document in 3 to 5 sentences, focusing on the main topics:\n\n{snippet}"
    )

    result = call_llm(prompt)
    if result:
        return result

    # Local fallback: extract first 3 sentences
    sentences = re.split(r"(?<=[.!?])\s+", snippet)
    summary = " ".join(sentences[:4])
    if len(summary) > 500:
        summary = summary[:497] + "..."
    return summary or "No summary available."


def summarize_context(context_texts: List[str], query: str) -> str:
    """Build a structured analysis from all retrieved document chunks."""
    snippets = [normalize_text(t) for t in context_texts if normalize_text(t)]
    if not snippets:
        return "No relevant document content was found in the uploaded documents to answer this question. Please upload the relevant documents first."

    sections = []
    for i, snippet in enumerate(snippets, 1):
        if len(snippet) > 50:
            sections.append(f"**Excerpt {i}:** {snippet}")

    combined_context = "\n\n".join(sections)

    response_parts = [
        f"## Analysis based on uploaded documents\n",
        f"**Query:** {query}\n",
        f"The following relevant sections were found in your documents:\n",
        combined_context,
        f"\n---\n",
        f"**Recommendation:** Review the excerpts above for details related to your query. "
        f"If more specific guidance is needed, try asking a more targeted question about a specific "
        f"component, failure mode, or procedure mentioned in the documents.",
    ]
    return "\n".join(response_parts)


# ---------------------------------------------------------------------------
# Document routes
# ---------------------------------------------------------------------------

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    saved = []
    for f in files:
        filename: str = f.filename or "unnamed_file"
        dest_path = os.path.join(UPLOAD_DIR, filename)
        base, ext = os.path.splitext(filename)
        idx = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(UPLOAD_DIR, f"{base}-{idx}{ext}")
            idx += 1

        content = await f.read()
        with open(dest_path, "wb") as out:
            out.write(content)

        # Extract text
        text = None
        if filename.lower().endswith(".txt"):
            text = content.decode("utf-8", errors="replace")
        elif filename.lower().endswith(".pdf"):
            text = extract_pdf_text(content)

        # Generate summary
        summary = None
        if text:
            try:
                summary = generate_summary(text)
            except Exception as e:
                print("summarization error", e)

        doc = Document(
            filename=os.path.basename(dest_path),
            filepath=dest_path,
            summary=summary,
            uploaded_by=current_user.id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        saved.append({"id": doc.id, "filename": doc.filename, "summary": doc.summary})

        # Generate embeddings with configurable chunk size and overlap
        if text:
            try:
                chunks = []
                start = 0
                while start < len(text):
                    end = start + settings.chunk_size
                    chunk = text[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    start += settings.chunk_size - settings.chunk_overlap

                hf = get_hf_client()
                vectors, metas = [], []
                for c in chunks:
                    cleaned = normalize_text(c)
                    emb = hf.embed_text(cleaned)
                    vectors.append(emb)
                    metas.append({
                        "doc_id": doc.id,
                        "filename": doc.filename,
                        "text": cleaned[:settings.chunk_metadata_length],
                    })
                hf.add_embeddings(vectors, metas)
            except Exception as e:
                print("embedding error", e)

    return {"saved": saved}


@router.get("/", status_code=status.HTTP_200_OK)
def list_documents(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    docs = (
        db.query(Document)
        .filter(Document.uploaded_by == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "summary": d.summary,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.uploaded_by == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        filepath = str(doc.filepath)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass
    db.delete(doc)
    db.commit()
    return {"deleted": doc_id}


@router.post("/search")
def search_docs(query: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = query.get("query") if isinstance(query, dict) else None
    top_k = int(query.get("top_k", settings.retrieval_top_k) if isinstance(query, dict) else settings.retrieval_top_k)
    if not q:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        hf = get_hf_client()
        qvec = hf.embed_text(q)
        hits = hf.search(qvec, top_k=top_k)
        return {"results": [{"id": h.get("id"), "meta": h.get("meta")} for h in hits]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Chat session routes
# ---------------------------------------------------------------------------

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "message_count": len(list(s.messages)),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "sources": json.loads(m.sources_json) if m.sources_json else [],
                "created_at": m.created_at.isoformat(),
            }
            for m in session.messages
        ],
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"deleted": session_id}


# ---------------------------------------------------------------------------
# Chat (streaming SSE)
# ---------------------------------------------------------------------------

@router.post("/chat/stream")
async def rag_chat_stream(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = payload.get("query") if isinstance(payload, dict) else None
    session_id = payload.get("session_id")
    top_k = int(payload.get("top_k", settings.retrieval_top_k) if isinstance(payload, dict) else settings.retrieval_top_k)
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    # Get or create session
    if session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id, ChatSession.user_id == current_user.id
        ).first()
        if not session:
            session_id = None

    if not session_id:
        session = ChatSession(user_id=current_user.id, title=query[:60])
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    # Build history context (configurable message limit)
    history_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(settings.history_message_limit)
        .all()
    )
    history_msgs = list(reversed(history_msgs))
    history_context = ""
    if history_msgs:
        lines = []
        for m in history_msgs:
            prefix = "User" if m.role == "user" else "Assistant"
            lines.append(f"{prefix}: {m.content}")
        history_context = "\n".join(lines) + "\n\n"

    # Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=query)
    db.add(user_msg)
    db.commit()

    # Semantic retrieval
    sources = []
    context = ""
    hits = []
    try:
        hf = get_hf_client()
        qvec = hf.embed_text(query)
        hits = hf.search(qvec, top_k=top_k)
        context_texts = [h["meta"].get("text", "") for h in hits if h.get("meta")]
        context = "\n\n---\n\n".join(context_texts)
        sources = [{"id": h.get("id"), "meta": h.get("meta")} for h in hits]
    except Exception as e:
        print("retrieval error", e)

    # Build prompt
    prompt = (
        f"{SYSTEM_PROMPT}"
        f"{history_context}"
        f"=== DOCUMENT CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
        f"User Question: {query}\n\n"
        f"Provide a detailed, structured answer:"
    )

    # Get full answer
    answer = call_llm(prompt)
    if not answer:
        answer = summarize_context(
            [h["meta"].get("text", "") for h in hits if h.get("meta")],
            query,
        )

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        sources_json=json.dumps(sources),
    )
    db.add(assistant_msg)
    if len(history_msgs) == 0 and session is not None:
        session.title = query[:60]  # type: ignore[assignment]
    from sqlalchemy.sql import func as sqlfunc
    if session is not None:
        session.updated_at = sqlfunc.now()  # type: ignore[assignment]
    db.commit()

    # Stream response word-by-word as SSE
    async def event_stream():
        meta = json.dumps({"session_id": session_id, "sources": sources})
        yield f"data: __META__{meta}\n\n"
        await asyncio.sleep(0)

        words = answer.split(" ")
        for i, word in enumerate(words):
            token = word if i == len(words) - 1 else word + " "
            yield f"data: {token}\n\n"
            await asyncio.sleep(0.04)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Non-streaming chat (kept for compatibility)
# ---------------------------------------------------------------------------

@router.post("/chat")
def rag_chat(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = payload.get("query") if isinstance(payload, dict) else None
    top_k = int(payload.get("top_k", settings.retrieval_top_k) if isinstance(payload, dict) else settings.retrieval_top_k)
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    try:
        hf = get_hf_client()
        qvec = hf.embed_text(query)
        hits = hf.search(qvec, top_k=top_k)
        context_texts = [h["meta"].get("text", "") for h in hits if h.get("meta")]
        context = "\n\n---\n\n".join(context_texts)
        sources = [{"id": h.get("id"), "meta": h.get("meta")} for h in hits]
        prompt = (
            f"{SYSTEM_PROMPT}"
            f"=== DOCUMENT CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
            f"User Question: {query}\n\n"
            f"Provide a detailed, structured answer:"
        )
        answer = call_llm(prompt) or summarize_context(context_texts, query)
        return {"answer": answer, "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
