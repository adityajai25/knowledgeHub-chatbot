import os
import io
from app.db.database import SessionLocal
from app.docs.chunking import chunk_text
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


def already_indexed(hf, doc_id):
    try:
        return hf.is_document_indexed(doc_id)
    except Exception:
        return False


def main():
    hf = get_hf_client()

    db = SessionLocal()
    docs = db.query(Document).all()
    uploaded_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    for doc in docs:
        if already_indexed(hf, doc.id):
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

        chunks = chunk_text(text, 500, 50)
        vectors = []
        metas = []
        for idx, c in enumerate(chunks):
            v = hf.embed_text(c)
            vectors.append(v)
            metas.append({
                'doc_id': doc.id,
                'chunk_index': idx,
                'filename': doc.filename,
                'text': c[:200],
            })
        hf.add_embeddings(vectors, metas)
        print(f"Indexed doc {doc.id} with {len(chunks)} chunks")

    print('Indexing complete')


if __name__ == '__main__':
    main()
