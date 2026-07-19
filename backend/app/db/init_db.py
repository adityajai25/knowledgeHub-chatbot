from app.db.database import Base, engine
# Import ALL models so create_all picks up every table & column
from app.models import User, Document, ChatSession, ChatMessage  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
