"""Pydantic response/request schemas."""

import re
import datetime
import uuid

from pydantic import BaseModel, Field, field_validator


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str | None
    email: str
    display_name: str
    avatar_url: str | None
    score: int
    answers_count: int
    is_admin: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    name: str
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 20:
            raise ValueError("Username must be 3–20 characters")
        if not re.match(r"^[A-Za-z0-9_]+$", v):
            raise ValueError("Username may only contain letters, numbers, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.match(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$", v):
            raise ValueError("Password must be at least 8 characters with at least one letter and one number")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=1, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)


class AuthSessionResponse(BaseModel):
    """Returned after login/register; JWT is only in HttpOnly cookie (not in body)."""

    user: UserResponse


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
    weekday: str | None = None
    local_date: str | None = None
    local_time: str | None = None


class NextQuestionResponse(BaseModel):
    question_id: str
    gps_point: GpsPointResponse
    candidates: list[PoiResponse]


class AnswerRequest(BaseModel):
    question_id: uuid.UUID
    selected_poi_id: str = Field(..., min_length=1, max_length=255)


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


class GpsPointInput(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    timestamp: datetime.datetime | None = None
    source: str | None = Field(None, max_length=255)


class GpsPointBulkRequest(BaseModel):
    points: list[GpsPointInput] = Field(..., max_length=5000)


class GpsPointBulkResponse(BaseModel):
    created: int
    total: int
