"""Admin endpoints: GPS point import and label export."""

import csv
import datetime
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.geo import lat_lon_to_h3
from app.models import Answer, GpsPoint, Question, User
from app.schemas import GpsPointBulkRequest, GpsPointBulkResponse
from app.services.poi_service import get_nearby_pois

router = APIRouter(prefix="/admin", tags=["admin"])

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_POI_QUALITY_SCAN = 200


def _excel_safe(value: object) -> str:
    """Prefix cells that could be interpreted as formulas when opened in Excel."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def _make_gps_point(
    lat: float,
    lon: float,
    timestamp: datetime.datetime | None,
    source: str | None,
) -> GpsPoint:
    return GpsPoint(
        lat=lat,
        lon=lon,
        timestamp=timestamp,
        source=source,
        h3_cell=lat_lon_to_h3(lat, lon),
    )


@router.post("/gps-points/bulk", response_model=GpsPointBulkResponse)
async def bulk_import_gps_points(
    body: GpsPointBulkRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    created = 0
    for point in body.points:
        db.add(_make_gps_point(point.lat, point.lon, point.timestamp, point.source))
        created += 1

    await db.flush()
    return {"created": created, "total": len(body.points)}


@router.post("/gps-points/upload-csv", response_model=GpsPointBulkResponse)
async def upload_gps_csv(
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a CSV file with columns: lat, lon, timestamp (optional), source (optional)."""
    content = await file.read()
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV file too large (max {MAX_CSV_BYTES // (1024 * 1024)} MB)",
        )

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from e

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV has no header row")

    required = {"lat", "lon"}
    headers = {h.strip().lower() for h in reader.fieldnames if h}
    if not required.issubset(headers):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns: {', '.join(sorted(required))}",
        )

    created = 0
    for row_num, raw in enumerate(reader, start=2):
        row = {k.strip().lower(): v for k, v in raw.items() if k}
        try:
            lat = float(row["lat"])
            lon = float(row["lon"])
        except (KeyError, TypeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid lat/lon on row {row_num}",
            ) from e

        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise HTTPException(
                status_code=400,
                detail=f"lat/lon out of range on row {row_num}",
            )

        timestamp = None
        if "timestamp" in row and row["timestamp"] and str(row["timestamp"]).strip():
            try:
                timestamp = datetime.datetime.fromisoformat(str(row["timestamp"]).strip())
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid timestamp on row {row_num}",
                ) from e

        source = row.get("source", None)
        if source is not None and isinstance(source, str):
            source = source.strip() or None

        db.add(_make_gps_point(lat, lon, timestamp, source))
        created += 1

    await db.flush()
    return {"created": created, "total": created}


def _streaming_export(payload: str, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([payload]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/labels")
async def export_labels(
    format: str = Query("csv", enum=["csv", "json"]),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export every individual annotation (one row per answer).

    Annotators are identified only by opaque user_id — no email/PII, so the
    file can be shared with research collaborators.
    """
    result = await db.execute(
        select(Answer, Question, GpsPoint)
        .join(Question, Answer.question_id == Question.id)
        .join(GpsPoint, Question.gps_point_id == GpsPoint.id)
        .order_by(Answer.created_at.asc())
    )
    rows = result.all()

    records = [
        {
            "answer_id": str(answer.id),
            "question_id": str(answer.question_id),
            "user_id": str(answer.user_id),
            "gps_lat": gps_point.lat,
            "gps_lon": gps_point.lon,
            "gps_timestamp": gps_point.timestamp.isoformat() if gps_point.timestamp else None,
            "h3_cell": question.h3_cell,
            "selected_poi_id": answer.selected_poi_id,
            "selected_distance_meters": answer.selected_distance_meters,
            "score_awarded": answer.score_awarded,
            "answered_at": answer.created_at.isoformat(),
        }
        for answer, question, gps_point in rows
    ]

    if format == "json":
        return _streaming_export(
            json.dumps(records, indent=2), "application/json", "labels.json"
        )

    output = io.StringIO()
    fieldnames = list(records[0].keys()) if records else [
        "answer_id", "question_id", "user_id", "gps_lat", "gps_lon",
        "gps_timestamp", "h3_cell", "selected_poi_id",
        "selected_distance_meters", "score_awarded", "answered_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        record["selected_poi_id"] = _excel_safe(record["selected_poi_id"])
        writer.writerow(record)
    output.seek(0)
    return _streaming_export(output.getvalue(), "text/csv", "labels.csv")


@router.get("/export/consensus")
async def export_consensus(
    format: str = Query("csv", enum=["csv", "json"]),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export the consensus dataset (one row per question).

    This is the ground-truth artifact for ML training: the consensus label,
    its confidence, the full vote distribution, and difficulty covariates.
    Questions still collecting answers export with status "active" and a
    null label; filter on status/locked_at for a frozen training set.
    """
    vote_result = await db.execute(
        select(
            Answer.question_id,
            Answer.selected_poi_id,
            func.count(Answer.id).label("cnt"),
        )
        .group_by(Answer.question_id, Answer.selected_poi_id)
    )
    votes_by_question: dict = {}
    for question_id, poi_id, cnt in vote_result.all():
        votes_by_question.setdefault(question_id, {})[poi_id] = cnt

    result = await db.execute(
        select(Question, GpsPoint)
        .join(GpsPoint, Question.gps_point_id == GpsPoint.id)
        .order_by(Question.created_at.asc())
    )
    rows = result.all()

    records = [
        {
            "question_id": str(question.id),
            "gps_lat": gps_point.lat,
            "gps_lon": gps_point.lon,
            "gps_timestamp": gps_point.timestamp.isoformat() if gps_point.timestamp else None,
            "h3_cell": question.h3_cell,
            "status": question.status,
            "consensus_poi_id": question.consensus_poi_id,
            "consensus_confidence": question.consensus_confidence,
            "votes_total": question.votes_total,
            "answers_target": question.answers_target,
            "candidate_density": question.candidate_density,
            "vote_distribution": votes_by_question.get(question.id, {}),
            "locked_at": question.locked_at.isoformat() if question.locked_at else None,
            "created_at": question.created_at.isoformat(),
        }
        for question, gps_point in rows
    ]

    if format == "json":
        return _streaming_export(
            json.dumps(records, indent=2), "application/json", "consensus.json"
        )

    output = io.StringIO()
    fieldnames = list(records[0].keys()) if records else [
        "question_id", "gps_lat", "gps_lon", "gps_timestamp", "h3_cell",
        "status", "consensus_poi_id", "consensus_confidence", "votes_total",
        "answers_target", "candidate_density", "vote_distribution",
        "locked_at", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        record["consensus_poi_id"] = _excel_safe(record["consensus_poi_id"] or "")
        record["vote_distribution"] = json.dumps(record["vote_distribution"])
        writer.writerow(record)
    output.seek(0)
    return _streaming_export(output.getvalue(), "text/csv", "consensus.csv")


@router.get("/poi-quality")
async def poi_quality_report(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    include_points: bool = Query(
        False,
        description="If true, include per-point breakdown for the scanned sample.",
    ),
) -> dict:
    """Check candidate density (scans at most 200 points to limit DB load)."""
    total_points = (await db.execute(select(func.count(GpsPoint.id)))).scalar_one()
    result = await db.execute(
        select(GpsPoint).order_by(GpsPoint.created_at.asc()).limit(MAX_POI_QUALITY_SCAN)
    )
    sample = result.scalars().all()
    report: list[dict] = []
    total_candidates = 0
    sparse_count = 0

    for gp in sample:
        pois = await get_nearby_pois(db, lat=gp.lat, lon=gp.lon)
        categories = {p["category"] for p in pois}
        count = len(pois)
        total_candidates += count
        if count < 3:
            sparse_count += 1
        if include_points:
            report.append({
                "gps_point_id": str(gp.id),
                "lat": gp.lat,
                "lon": gp.lon,
                "candidate_count": count,
                "unique_categories": len(categories),
                "categories": sorted(categories),
            })

    n = len(sample)
    return {
        "total_gps_points": total_points,
        "scanned_points": n,
        "scan_truncated": total_points > MAX_POI_QUALITY_SCAN,
        "sparse_points_in_sample": sparse_count,
        "avg_candidates_in_sample": round(total_candidates / max(n, 1), 1),
        "points": report,
    }
