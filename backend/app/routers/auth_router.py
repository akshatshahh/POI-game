"""Auth endpoints: local register/login + Google OAuth2."""

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    clear_access_token_cookie,
    clear_oauth_state_cookie,
    create_access_token,
    get_current_user,
    get_password_hash,
    set_access_token_cookie,
    set_oauth_state_cookie,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import (
    AuthSessionResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    response = RedirectResponse(url=url)
    set_oauth_state_cookie(response, state)
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    frontend = settings.frontend_url.rstrip("/")

    def fail_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{frontend}/login?error=oauth")

    if error:
        return fail_redirect()

    cookie_state = request.cookies.get("oauth_state")
    if not code or not state or not cookie_state:
        return fail_redirect()

    if not secrets.compare_digest(cookie_state, state):
        return fail_redirect()

    redirect_uri = f"{settings.backend_url}/auth/google/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    google_id = userinfo["id"]
    email = userinfo["email"]
    display_name = userinfo.get("name", email)
    avatar_url = userinfo.get("picture")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.flush()
    else:
        user.display_name = display_name
        user.avatar_url = avatar_url
        await db.flush()

    access_token = create_access_token(user.id)

    response = RedirectResponse(url=f"{frontend}/")
    clear_oauth_state_cookie(response)
    set_access_token_cookie(response, access_token)
    return response


@router.post("/register", response_model=AuthSessionResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    existing = await db.execute(
        select(User).where(
            or_(User.username == body.username, User.email == body.email)
        )
    )
    conflict = existing.scalar_one_or_none()
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail="Could not create account with the provided username or email",
        )

    user = User(
        username=body.username,
        email=body.email,
        display_name=body.name,
        password_hash=get_password_hash(body.password),
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id)
    payload = AuthSessionResponse(user=UserResponse.model_validate(user)).model_dump(mode="json")
    response = JSONResponse(content=payload)
    set_access_token_cookie(response, token)
    return response


@router.post("/login", response_model=AuthSessionResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    identifier = body.username_or_email.strip().lower()
    result = await db.execute(
        select(User).where(
            or_(
                User.username == body.username_or_email.strip(),
                User.email == identifier,
            )
        )
    )
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id)
    payload = AuthSessionResponse(user=UserResponse.model_validate(user)).model_dump(mode="json")
    response = JSONResponse(content=payload)
    set_access_token_cookie(response, token)
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"ok": True})
    clear_access_token_cookie(response)
    return response
