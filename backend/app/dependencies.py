from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.identity import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación requerida")
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Token inválido o vencido") from exc
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if user is None or user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="Cuenta no disponible")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

