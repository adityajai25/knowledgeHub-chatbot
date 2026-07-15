from sqlalchemy.orm import Session

from app.models import User
from app.auth.schemas import UserCreate
from app.auth.utils import get_password_hash


def create_user(db: Session, user_in: UserCreate) -> User:
    db_user = User(email=user_in.email, hashed_password=get_password_hash(user_in.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()
