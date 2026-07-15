from typing import Optional

from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.auth.service import get_user_by_email


def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid auth header")
    return parts[1]


def get_current_user(token: str = Depends(get_token_from_header), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject: str = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_email(db, subject)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
