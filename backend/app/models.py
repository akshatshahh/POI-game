import datetime
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    answers_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    answers: Mapped[list["Answer"]] = relationship(back_populates="user")


class GpsPoint(Base):
    __tablename__ = "gps_points"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    h3_cell: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    questions: Mapped[list["Question"]] = relationship(back_populates="gps_point")


class Question(Base):
    """One labeling task for a GPS point.

    Lifecycle: active -> consensus_reached | no_consensus (both terminal,
    marked by locked_at). Terminal questions reject new answers and their
    GPS points are excluded from question selection.
    """

    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gps_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gps_points.id"), nullable=False, index=True
    )
    h3_cell: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", server_default="active")
    # The full nearby-POI set frozen at question creation. Answers are
    # validated against this list so the exported dataset can reconstruct
    # exactly which choices annotators had.
    candidates: Mapped[list | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    # Number of POIs within the search radius; a difficulty proxy exported
    # with every label (dense areas are harder to annotate).
    candidate_density: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # How many independent answers this question collects before a consensus
    # decision is final. Starts at the base target; escalates when annotators
    # disagree or the area is dense.
    answers_target: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    votes_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    consensus_poi_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Fraction of votes on the winning POI at lock time (top_votes / total).
    consensus_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    locked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    gps_point: Mapped["GpsPoint"] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_answers_user_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    selected_poi_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Distance from the GPS point to the selected POI, kept as an ML covariate
    # (it no longer affects scoring).
    selected_distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Score components are stored explicitly so consensus can be re-evaluated
    # (and constants tuned) without decoding anything from the total.
    base_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    distance_bonus: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    consensus_bonus: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    score_awarded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question: Mapped["Question"] = relationship(back_populates="answers")
    user: Mapped["User"] = relationship(back_populates="answers")
