"""Pydantic response/request schemas."""

import datetime
import uuid

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None
    score: int
    answers_count: int
    is_admin: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class PoiResponse(BaseModel):
    id: str
    name: str
    category: str
    lat: float
    lon: float
    distance_meters: float


class GpsPointResponse(BaseModel):
    lat: float
    lon: float
    timestamp: str | None


class NextQuestionResponse(BaseModel):
    question_id: str
    gps_point: GpsPointResponse
    candidates: list[PoiResponse]


class AnswerRequest(BaseModel):
    question_id: uuid.UUID
    selected_poi_id: str


class AnswerResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    selected_poi_id: str
    score_awarded: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    avatar_url: str | None
    score: int
    answers_count: int
