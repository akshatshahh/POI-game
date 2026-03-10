"""Game endpoints: next question, answer submission."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import NextQuestionResponse
from app.services.question_service import get_next_question

router = APIRouter(prefix="/game", tags=["game"])


@router.get("/next-question", response_model=NextQuestionResponse)
async def next_question(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await get_next_question(db, user_id=user.id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No more questions available. Check back later!",
        )
    return result
