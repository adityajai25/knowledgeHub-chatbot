import os
import json
from typing import List, Optional

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
        self.meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'embeddings_meta.json')
        self.vectors_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'embeddings_vectors.json')
        self._load()

    def _load(self):
        if os.path.exists(self.meta_path) and os.path.exists(self.vectors_path):
            with open(self.meta_path, 'r') as f:
                self.meta = json.load(f)
            with open(self.vectors_path, 'r') as f:
                self.vectors = json.load(f)
        else:
            self.meta = {}
            self.vectors = []

    def _save(self):
        with open(self.meta_path, 'w') as f:
            json.dump(self.meta, f)
        with open(self.vectors_path, 'w') as f:
            json.dump(self.vectors, f)

    def embed_text(self, text: str) -> List[float]:
        headers = {"Authorization": f"Bearer {settings.hf_api_key}"} if settings.hf_api_key else {}
        payload = {"inputs": text}
        resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # if nested tokens, average
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            arr = np.array(data, dtype=float)
            return arr.mean(axis=0).tolist()
        return data

    def add_embeddings(self, vectors: List[List[float]], metas: List[dict]):
        start = len(self.vectors)
        for i, v in enumerate(vectors):
            self.vectors.append(v)
            self.meta[str(start + i)] = metas[i]
        self._save()

    def search(self, query_vec: List[float], top_k: int = 5):
        if len(self.vectors) == 0:
            return []
        arr = np.array(self.vectors, dtype=float)
        q = np.array(query_vec, dtype=float)
        norms = np.linalg.norm(arr, axis=1) * (np.linalg.norm(q) + 1e-12)
        sims = (arr @ q) / norms
        idxs = np.argsort(-sims)[:top_k]
        results = []
        for idx in idxs:
            results.append({
                'id': int(idx),
                'score': float(sims[idx]),
                'meta': self.meta.get(str(idx))
            })
        return results


class APIEmbeddings(BaseEmbeddings):
    def __init__(self):
        token = settings.hf_api_key
        if not token:
            raise RuntimeError("Hugging Face API key not configured (HF_API_KEY)")
        self.token = token
        self.model = settings.hf_embedding_model
        self.meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'embeddings_meta.json')
        self.vectors_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'embeddings_vectors.json')
        self._load()

    def _load(self):
        if os.path.exists(self.meta_path) and os.path.exists(self.vectors_path):
            with open(self.meta_path, 'r') as f:
                self.meta = json.load(f)
            with open(self.vectors_path, 'r') as f:
                self.vectors = json.load(f)
        else:
            self.meta = {}
            self.vectors = []

    def _save(self):
        with open(self.meta_path, 'w') as f:
            json.dump(self.meta, f)
        with open(self.vectors_path, 'w') as f:
            json.dump(self.vectors, f)

    def embed_text(self, text: str) -> List[float]:
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model}"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"inputs": text}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            arr = np.array(data, dtype=float)
            vec = arr.mean(axis=0).tolist()
            return vec
        return data

    def add_embeddings(self, vectors: List[List[float]], metas: List[dict]):
        start = len(self.vectors)
        for i, v in enumerate(vectors):
            self.vectors.append(v)
            self.meta[str(start + i)] = metas[i]
        self._save()

    def search(self, query_vec: List[float], top_k: int = 5):
        if len(self.vectors) == 0:
            return []
        arr = np.array(self.vectors, dtype=float)
        q = np.array(query_vec, dtype=float)
        norms = np.linalg.norm(arr, axis=1) * (np.linalg.norm(q) + 1e-12)
        sims = (arr @ q) / norms
        idxs = np.argsort(-sims)[:top_k]
        results = []
        for idx in idxs:
            results.append({
                'id': int(idx),
                'score': float(sims[idx]),
                'meta': self.meta.get(str(idx))
            })
        return results


class LocalEmbeddings(BaseEmbeddings):
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            raise RuntimeError('Local sentence-transformers not installed. Run: pip install -U sentence-transformers') from e
        self.model_name = settings.hf_embedding_model.split('/')[-1]
        # If model name is a full repo path, use that; otherwise default to the model string
        self.model = SentenceTransformer(settings.hf_embedding_model)
        self.meta_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'embeddings_meta.json')
        self.vectors_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'embeddings_vectors.json')
        self._load()

    def _load(self):
        if os.path.exists(self.meta_path) and os.path.exists(self.vectors_path):
            with open(self.meta_path, 'r') as f:
                self.meta = json.load(f)
            with open(self.vectors_path, 'r') as f:
                self.vectors = json.load(f)
        else:
            self.meta = {}
            self.vectors = []

    def _save(self):
        with open(self.meta_path, 'w') as f:
            json.dump(self.meta, f)
        with open(self.vectors_path, 'w') as f:
            json.dump(self.vectors, f)

    def embed_text(self, text: str) -> List[float]:
        vec = self.model.encode(text)
        return vec.tolist() if hasattr(vec, 'tolist') else list(vec)

    def add_embeddings(self, vectors: List[List[float]], metas: List[dict]):
        start = len(self.vectors)
        for i, v in enumerate(vectors):
            self.vectors.append(v)
            self.meta[str(start + i)] = metas[i]
        self._save()

    def search(self, query_vec: List[float], top_k: int = 5):
        if len(self.vectors) == 0:
            return []
        arr = np.array(self.vectors, dtype=float)
        q = np.array(query_vec, dtype=float)
        norms = np.linalg.norm(arr, axis=1) * (np.linalg.norm(q) + 1e-12)
        sims = (arr @ q) / norms
        idxs = np.argsort(-sims)[:top_k]
        results = []
        for idx in idxs:
            results.append({
                'id': int(idx),
                'score': float(sims[idx]),
                'meta': self.meta.get(str(idx))
            })
        return results


hf_embeddings: Optional[BaseEmbeddings] = None


def get_hf_client():
    global hf_embeddings
    if hf_embeddings is None:
        # priority: endpoint -> local cache -> api
        # Prefer local embeddings in environments where outbound HF DNS is blocked.
        if settings.hf_inference_endpoint:
            hf_embeddings = EndpointEmbeddings()
        else:
            try:
                hf_embeddings = LocalEmbeddings()
            except Exception:
                if settings.hf_api_key:
                    hf_embeddings = APIEmbeddings()
                else:
                    raise
    return hf_embeddings
