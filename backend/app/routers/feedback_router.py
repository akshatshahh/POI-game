"""Save voluntary logout feedback; only administrators can read it."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Feedback, User
from app.rate_limit import RateLimiter
from app.schemas import FeedbackRequest, FeedbackReceipt, FeedbackResponse

router = APIRouter(tags=["feedback"])
feedback_rate_limiter = RateLimiter(times=5, seconds=15 * 60)


@router.post("/feedback", response_model=FeedbackReceipt, status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    _user: User = Depends(get_current_user),
    _limit: None = Depends(feedback_rate_limiter),
    db: AsyncSession = Depends(get_db),
) -> Feedback:
    feedback = Feedback(**body.model_dump())
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


@router.get("/admin/feedback", response_model=list[FeedbackResponse])
async def list_feedback(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[Feedback]:
    result = await db.execute(
        select(Feedback).order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .limit(limit).offset(offset)
    )
    return list(result.scalars().all())
