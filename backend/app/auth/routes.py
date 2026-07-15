from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.auth.schemas import Token, UserCreate, UserOut
from app.auth.service import create_user, get_user_by_email
from app.auth.utils import verify_password, get_password_hash
from app.core.config import settings
from app.db.database import get_db

router = APIRouter()


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


# password helpers are provided by app.auth.utils


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = create_user(db, user)
    return {"id": new_user.id, "email": new_user.email}


@router.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.email)
    return {"access_token": token, "token_type": "bearer"}
