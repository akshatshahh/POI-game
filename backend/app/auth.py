"""Authentication utilities: JWT creation/verification, password hashing, current-user dependency."""

import datetime
import uuid

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.config import settings
from app.database import get_db
from app.models import User

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30
JWT_AUDIENCE = "poi-game"

ACCESS_TOKEN_COOKIE = "access_token"
OAUTH_STATE_COOKIE = "oauth_state"
TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def is_cookie_secure() -> bool:
    return settings.backend_url.startswith("https")


def set_access_token_cookie(response: Response, token: str) -> None:
    secure = is_cookie_secure()
    # Cross-origin SPA (e.g. separate Railway hostnames) needs None + Secure.
    samesite: str = "none" if secure else "lax"
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=secure,
        max_age=TOKEN_COOKIE_MAX_AGE,
        samesite=samesite,
        path="/",
    )


def clear_access_token_cookie(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")


def set_oauth_state_cookie(response: Response, state: str) -> None:
    secure = is_cookie_secure()
    samesite: str = "none" if secure else "lax"
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=secure,
        max_age=600,
        samesite=samesite,
        path="/",
    )


def clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")


def get_password_hash(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return uuid.UUID(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()

    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if token:
        return token

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(request)
    user_id = decode_access_token(token)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
