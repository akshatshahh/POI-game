"""Game endpoints: next question, answer submission."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Answer, GpsPoint, Question, User
from app.schemas import AnswerRequest, AnswerResponse, NextQuestionResponse
from app.services.poi_service import get_nearby_pois
from app.services.question_service import get_next_question
from app.services.scoring_service import compute_score, retroactive_score_update

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

    candidates = await get_nearby_pois(db, lat=gps_point.lat, lon=gps_point.lon)
    candidate_map = {c["id"]: c for c in candidates}
    if body.selected_poi_id not in candidate_map:
        raise HTTPException(
            status_code=400,
            detail="Selected POI is not a valid candidate for this question",
        )

    selected_distance = candidate_map[body.selected_poi_id]["distance_meters"]

    answer = Answer(
        question_id=body.question_id,
        user_id=user.id,
        selected_poi_id=body.selected_poi_id,
    )
    db.add(answer)
    await db.flush()

    score = await compute_score(db, body.question_id, body.selected_poi_id, selected_distance)
    answer.score_awarded = score
    user.score += score
    user.answers_count += 1
    await db.flush()

    await retroactive_score_update(db, body.question_id)

    return answer
