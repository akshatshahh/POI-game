"""Game endpoints: next question, answer submission."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Answer, GpsPoint, Question, User
from app.schemas import AnswerRequest, AnswerResponse, NextQuestionResponse
from app.services.question_service import (
    ensure_question_candidates,
    get_next_question,
)
from app.services.scoring_service import apply_initial_score, evaluate_consensus

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


@router.post("/answer", response_model=AnswerResponse)
async def submit_answer(
    body: AnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Answer:
    result = await db.execute(
        select(Question).where(Question.id == body.question_id)
    )
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.locked_at is not None:
        raise HTTPException(
            status_code=409,
            detail="This question has already been finalized",
        )

    existing = await db.execute(
        select(Answer).where(
            Answer.question_id == body.question_id,
            Answer.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Already answered this question")

    gp_result = await db.execute(
        select(GpsPoint).where(GpsPoint.id == question.gps_point_id)
    )
    gps_point = gp_result.scalar_one()

    # Answers are validated against the candidate set frozen on the question
    # at creation, so the accepted choice set is stable and reproducible.
    await ensure_question_candidates(db, question, gps_point)
    candidate_map = {c["id"]: c for c in question.candidates or []}
    if body.selected_poi_id not in candidate_map:
        raise HTTPException(
            status_code=400,
            detail="Selected POI is not a valid candidate for this question",
        )

    selected_distance = candidate_map[body.selected_poi_id].get("distance_meters")

    answer = Answer(
        question_id=body.question_id,
        user_id=user.id,
        selected_poi_id=body.selected_poi_id,
    )
    db.add(answer)
    try:
        await db.flush()
    except IntegrityError:
        # Two concurrent submits raced past the check above; the unique
        # constraint on (user_id, question_id) catches the loser.
        raise HTTPException(status_code=409, detail="Already answered this question")

    user.score += apply_initial_score(answer, selected_distance)
    user.answers_count += 1
    await db.flush()

    await evaluate_consensus(db, question)

    return answer
