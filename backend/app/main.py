from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.docs.routes import router as docs_router
from app.db.init_db import init_db

app = FastAPI(title="KnowledgeHub AI API", version="0.1.0")

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(docs_router, prefix="/api/docs", tags=["docs"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
