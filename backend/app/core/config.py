from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "KnowledgeHub AI"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/knowledgehub"
    secret_key: str = "dev-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    hf_api_key: Optional[str] = None
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_generation_model: str = "google/flan-t5-small"
    hf_inference_endpoint: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
