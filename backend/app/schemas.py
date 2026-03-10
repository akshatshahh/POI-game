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
