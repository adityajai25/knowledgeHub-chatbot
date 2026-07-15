import os
import io
from app.db.database import SessionLocal
from app.models import Document
from app.embeddings.hf_client import get_hf_client
from PyPDF2 import PdfReader


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [p.extract_text() or '' for p in reader.pages]
        text = '\n'.join(pages).strip()
        if text:
            return text
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
            return text
    except Exception:
        pass

    return ''


def extract_text_from_file(path):
    if path.lower().endswith('.txt'):
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    if path.lower().endswith('.pdf'):
        with open(path, 'rb') as f:
            return extract_pdf_text(f.read())
    return None


def already_indexed(meta, doc_id):
    for v in meta.values():
        if v.get('doc_id') == doc_id:
            return True
    return False


def main():
    hf = get_hf_client()
    # load existing meta
    meta = hf.meta

    db = SessionLocal()
    docs = db.query(Document).all()
    uploaded_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    for doc in docs:
        if already_indexed(meta, doc.id):
            print(f"Skipping doc {doc.id} already indexed")
            continue
        path = doc.filepath
        if not os.path.exists(path):
            # try uploaded_dir
            path = os.path.join(uploaded_dir, doc.filename)
            if not os.path.exists(path):
                print(f"File for doc {doc.id} not found: {doc.filepath}")
                continue

        text = extract_text_from_file(path)
        if not text:
            print(f"No text extracted for doc {doc.id} ({doc.filename})")
            continue

        chunks = [text[i:i+500] for i in range(0, len(text), 500) if text[i:i+500].strip()]
        vectors = []
        metas = []
        for c in chunks:
            v = hf.embed_text(c)
            vectors.append(v)
            metas.append({'doc_id': doc.id, 'text': c[:200]})
        hf.add_embeddings(vectors, metas)
        print(f"Indexed doc {doc.id} with {len(chunks)} chunks")

    print('Indexing complete')


if __name__ == '__main__':
    main()
