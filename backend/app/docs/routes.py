import os
import re
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.auth.deps import get_current_user
from app.models import Document
from app.embeddings.hf_client import get_hf_client
from PyPDF2 import PdfReader
import io
from app.core.config import settings


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [p.extract_text() or '' for p in reader.pages]
        text = '\n'.join(pages).strip()
        if text:
            return normalize_text(text)
    except Exception:
        pass

    try:
        from pdf2image import convert_from_bytes
        from pytesseract import image_to_string

        images = convert_from_bytes(content)
        texts = []
        for img in images:
            texts.append(image_to_string(img))
        text = '\n'.join(texts).strip()
        if text:
            return normalize_text(text)
    except Exception:
        pass

    return ''

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'uploads')
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def normalize_text(text: str) -> str:
    if not text:
        return ''
    text = text.replace('\u0000', ' ').replace('\x0c', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    return text.strip()


def summarize_context(context_texts: List[str], query: str) -> str:
    snippets = [normalize_text(t) for t in context_texts if normalize_text(t)]
    if not snippets:
        return 'No relevant document content is available for a summary yet.'

    combined = ' '.join(snippets[:3])
    sentences = re.split(r'(?<=[.!?])\s+', combined)
    summary = ' '.join(sentences[:3])
    if len(summary) > 600:
        summary = summary[:597].rstrip() + '...'
    if summary:
        return f"Based on the uploaded documents, the key idea appears to be: {summary}"
    return 'No summary could be generated from the available content.'


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(files: List[UploadFile] = File(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    saved = []
    for f in files:
        filename = f.filename
        dest_path = os.path.join(UPLOAD_DIR, filename)
        # prevent overwriting by appending a numeric suffix if exists
        base, ext = os.path.splitext(filename)
        idx = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(UPLOAD_DIR, f"{base}-{idx}{ext}")
            idx += 1

        with open(dest_path, "wb") as out:
            content = await f.read()
            out.write(content)

        doc = Document(filename=os.path.basename(dest_path), filepath=dest_path, uploaded_by=current_user.id)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        saved.append({"id": doc.id, "filename": doc.filename})

        # attempt to extract text and generate embeddings via Hugging Face
        try:
            text = None
            if filename.lower().endswith('.txt'):
                text = content.decode('utf-8', errors='replace')
            elif filename.lower().endswith('.pdf'):
                text = extract_pdf_text(content)

            if text:
                # simple chunking by 500 chars
                chunks = [text[i:i+500] for i in range(0, len(text), 500) if text[i:i+500].strip()]
                hf = get_hf_client()
                vectors = []
                metas = []
                for c in chunks:
                    cleaned_chunk = normalize_text(c)
                    emb = hf.embed_text(cleaned_chunk)
                    vectors.append(emb)
                    metas.append({"doc_id": doc.id, "text": cleaned_chunk[:200]})
                hf.add_embeddings(vectors, metas)
        except Exception as e:
            # don't block upload on embedding errors
            print('embedding error', e)

    return {"saved": saved}


@router.get("/", status_code=status.HTTP_200_OK)
def list_documents(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    docs = db.query(Document).filter(Document.uploaded_by == current_user.id).order_by(Document.uploaded_at.desc()).all()
    return [{"id": d.id, "filename": d.filename, "uploaded_at": d.uploaded_at.isoformat()} for d in docs]


@router.post('/search')
def search_docs(query: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = query.get('query') if isinstance(query, dict) else None
    top_k = int(query.get('top_k', 5) if isinstance(query, dict) else 5)
    if not q:
        raise HTTPException(status_code=400, detail='query is required')
    try:
        hf = get_hf_client()
        qvec = hf.embed_text(q)
        hits = hf.search(qvec, top_k=top_k)
        clean_hits = []
        for hit in hits:
            clean_hits.append({
                'id': hit.get('id'),
                'meta': hit.get('meta')
            })
        return {'results': clean_hits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/chat')
def rag_chat(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    query = payload.get('query') if isinstance(payload, dict) else None
    top_k = int(payload.get('top_k', 3) if isinstance(payload, dict) else 3)
    if not query:
        raise HTTPException(status_code=400, detail='query is required')

    try:
        hf = get_hf_client()
        qvec = hf.embed_text(query)
        hits = hf.search(qvec, top_k=top_k)

        # build context from hits
        context_texts = [h['meta'].get('text', '') for h in hits if h.get('meta')]
        context = '\n\n---\n\n'.join(context_texts)
        prompt = f"Use the following context to answer the question. Context:\n{context}\n\nQuestion: {query}\n\nAnswer concisely and cite sources."

        clean_sources = []
        for hit in hits:
            clean_sources.append({
                'id': hit.get('id'),
                'meta': hit.get('meta')
            })

        # generation: prefer configured HF endpoint/API, but fall back to a grounded summary
        import requests
        answer = None
        if settings.hf_inference_endpoint or settings.hf_api_key:
            try:
                if settings.hf_inference_endpoint:
                    url = settings.hf_inference_endpoint
                else:
                    url = f"https://api-inference.huggingface.co/models/{settings.hf_generation_model}"
                headers = {"Authorization": f"Bearer {settings.hf_api_key}"} if settings.hf_api_key else {}
                data = {"inputs": prompt, "parameters": {"max_new_tokens": 256}}
                resp = requests.post(url, headers=headers, json=data, timeout=60)
                resp.raise_for_status()
                gen = resp.json()
                if isinstance(gen, list) and len(gen) > 0 and 'generated_text' in gen[0]:
                    answer = gen[0]['generated_text']
                elif isinstance(gen, dict) and 'generated_text' in gen:
                    answer = gen['generated_text']
                else:
                    answer = str(gen)
            except Exception:
                answer = summarize_context(context_texts, query)
        else:
            # local generation via transformers
            try:
                from transformers import pipeline
                gen_pipe = pipeline('text2text-generation', model=settings.hf_generation_model)
                out = gen_pipe(prompt, max_new_tokens=256)
                if isinstance(out, list) and len(out) > 0 and 'generated_text' in out[0]:
                    answer = out[0]['generated_text']
                else:
                    answer = str(out)
            except Exception:
                answer = summarize_context(context_texts, query)

        return {"answer": answer, "sources": clean_sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
