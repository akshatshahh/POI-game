"""Leaderboard endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LeaderboardEntry

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(User)
        .where(User.answers_count > 0)
        .order_by(User.score.desc())
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        {
            "rank": idx + 1,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "score": user.score,
            "answers_count": user.answers_count,
        }
        for idx, user in enumerate(users)
    ]
