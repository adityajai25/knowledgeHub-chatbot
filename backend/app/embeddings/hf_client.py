import os
from typing import List, Optional, Dict, Any

import numpy as np
import requests

from app.core.config import settings


class BaseEmbeddings:
    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError()

    def add_embeddings(self, vectors: List[List[float]], metas: List[dict]):
        raise NotImplementedError()

    def search(self, query_vec: List[float], top_k: int = 5):
        raise NotImplementedError()


class EndpointEmbeddings(BaseEmbeddings):
    def __init__(self):
        self.endpoint = settings.hf_inference_endpoint
        if not self.endpoint:
            raise RuntimeError('HF inference endpoint not configured')

    def embed_text(self, text: str) -> List[float]:
        headers = {"Authorization": f"Bearer {settings.hf_api_key}"} if settings.hf_api_key else {}
        payload = {"inputs": text}
        resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            arr = np.array(data, dtype=float)
            return arr.mean(axis=0).tolist()
        return data


class APIEmbeddings(BaseEmbeddings):
    def __init__(self):
        token = settings.hf_api_key
        if not token:
            raise RuntimeError("Hugging Face API key not configured (HF_API_KEY)")
        self.token = token
        self.model = settings.hf_embedding_model

    def embed_text(self, text: str) -> List[float]:
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"inputs": text}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            arr = np.array(data, dtype=float)
            return arr.mean(axis=0).tolist()
        return data


class LocalEmbeddings(BaseEmbeddings):
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            raise RuntimeError('Local sentence-transformers not installed. Run: pip install -U sentence-transformers') from e
        self.model = SentenceTransformer(settings.hf_embedding_model)

    def embed_text(self, text: str) -> List[float]:
        vec = self.model.encode(text)
        return vec.tolist() if hasattr(vec, 'tolist') else list(vec)


class ChromaEmbeddings(BaseEmbeddings):
    def __init__(self, embedder: BaseEmbeddings):
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except Exception as e:
            raise RuntimeError('ChromaDB is not installed. Run: pip install chromadb') from e

        self.embedder = embedder
        self.persist_directory = os.path.abspath(settings.chroma_persist_directory)
        os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.Client(
            settings=ChromaSettings(
                persist_directory=self.persist_directory,
                is_persistent=True,
            )
        )
        self.collection = self.client.get_or_create_collection(
            name="knowledgehub",
            metadata={"source": "knowledgehub"},
        )

    def embed_text(self, text: str) -> List[float]:
        return self.embedder.embed_text(text)

    def add_embeddings(self, vectors: List[List[float]], metas: List[dict]):
        ids = []
        documents = []
        for meta in metas:
            doc_id = meta.get("doc_id")
            chunk_index = meta.get("chunk_index")
            if doc_id is None or chunk_index is None:
                raise ValueError("meta must include doc_id and chunk_index for Chroma storage")
            ids.append(f"doc-{doc_id}-chunk-{chunk_index}")
            documents.append(str(meta.get("text", "")))

        try:
            self.collection.delete(ids=ids)
        except Exception:
            pass

        self.collection.add(
            ids=ids,
            embeddings=vectors,
            metadatas=metas,
            documents=documents,
        )

    def search(self, query_vec: List[float], top_k: int = 5):
        if self.collection.count() == 0:
            return []

        result = self.collection.query(
            query_embeddings=query_vec,
            n_results=top_k,
            include=["metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        results = []
        for idx, meta, dist in zip(ids, metadatas, distances):
            score = 1.0 - float(dist) if dist is not None else 0.0
            results.append({"id": idx, "score": score, "meta": meta})
        return results

    def delete_by_doc_id(self, doc_id: int):
        ids_to_delete = []
        try:
            result = self.collection.get(where={"doc_id": doc_id}, include=["metadatas", "documents"])
            ids_to_delete = result.get("ids", [[]])[0]
        except Exception as e:
            print(f"vector delete lookup error: {e}")

        if ids_to_delete:
            try:
                self.collection.delete(ids=ids_to_delete)
                self.client.persist()
                return
            except Exception as e:
                print(f"vector delete by ids error: {e}")

        try:
            self.collection.delete(where={"doc_id": doc_id})
            self.client.persist()
        except Exception as e:
            print(f"vector delete by where error: {e}")

    def is_document_indexed(self, doc_id: int) -> bool:
        try:
            result = self.collection.get(
                where={"doc_id": doc_id},
                include=["metadatas"],
            )
            metadatas = result.get("metadatas", [[]])[0]
            return bool(metadatas)
        except Exception:
            return False


hf_embeddings: Optional[BaseEmbeddings] = None


def get_hf_client():
    global hf_embeddings
    if hf_embeddings is None:
        if settings.hf_inference_endpoint:
            base = EndpointEmbeddings()
        else:
            try:
                base = LocalEmbeddings()
            except Exception:
                if settings.hf_api_key:
                    base = APIEmbeddings()
                else:
                    raise
        hf_embeddings = ChromaEmbeddings(base)
    return hf_embeddings
