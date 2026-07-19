from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "KnowledgeHub AI"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:postgres@localhost:5432/knowledgehub"

    # ── Auth / JWT ───────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ── LLM Provider: "ollama" | "huggingface" ───────────────────────────
    llm_provider: str = "ollama"

    # ── Ollama settings ─────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout: int = 120

    # ── HuggingFace settings (fallback if llm_provider=huggingface) ─────
    hf_api_key: Optional[str] = None
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_generation_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    hf_inference_endpoint: Optional[str] = None

    # ── RAG Pipeline Tuning ──────────────────────────────────────────────
    chunk_size: int = 1500
    chunk_overlap: int = 200
    chunk_metadata_length: int = 1000
    retrieval_top_k: int = 8
    max_new_tokens: int = 1024
    llm_temperature: float = 0.3
    summary_snippet_length: int = 3000
    history_message_limit: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
