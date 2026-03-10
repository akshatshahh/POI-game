"""Google OAuth2 login endpoints."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserResponse

import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
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

    response = RedirectResponse(url=f"{settings.frontend_url}/?token={access_token}")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url=settings.frontend_url)
    response.delete_cookie("access_token")
    return response
