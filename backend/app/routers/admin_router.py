"""Admin endpoints: GPS point import and label export."""

import csv
import io
import datetime

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Answer, GpsPoint, Question, User
from app.schemas import GpsPointBulkRequest, GpsPointBulkResponse
from app.services.poi_service import get_nearby_pois

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/gps-points/bulk", response_model=GpsPointBulkResponse)
async def bulk_import_gps_points(
    body: GpsPointBulkRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    created = 0
    for point in body.points:
        gps = GpsPoint(
            lat=point.lat,
            lon=point.lon,
            timestamp=point.timestamp,
            source=point.source,
        )
        db.add(gps)
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
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    for row in reader:
        lat = float(row["lat"])
        lon = float(row["lon"])
        timestamp = None
        if "timestamp" in row and row["timestamp"]:
            timestamp = datetime.datetime.fromisoformat(row["timestamp"])
        source = row.get("source", None)

        gps = GpsPoint(lat=lat, lon=lon, timestamp=timestamp, source=source)
        db.add(gps)
        created += 1

    await db.flush()
    return {"created": created, "total": created}


@router.get("/export/labels")
async def export_labels(
    format: str = Query("csv", enum=["csv", "json"]),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export all labels as CSV or JSON for ML training pipelines."""
    result = await db.execute(
        select(Answer, Question, GpsPoint, User)
        .join(Question, Answer.question_id == Question.id)
        .join(GpsPoint, Question.gps_point_id == GpsPoint.id)
        .join(User, Answer.user_id == User.id)
        .order_by(Answer.created_at.asc())
    )
    rows = result.all()

    if format == "json":
        import json
        records = [
            {
                "answer_id": str(answer.id),
                "question_id": str(answer.question_id),
                "user_id": str(answer.user_id),
                "user_email": user.email,
                "gps_lat": gps_point.lat,
                "gps_lon": gps_point.lon,
                "gps_timestamp": gps_point.timestamp.isoformat() if gps_point.timestamp else None,
                "selected_poi_id": answer.selected_poi_id,
                "score_awarded": answer.score_awarded,
                "answered_at": answer.created_at.isoformat(),
            }
            for answer, _question, gps_point, user in rows
        ]
        return StreamingResponse(
            iter([json.dumps(records, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=labels.json"},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "answer_id", "question_id", "user_id", "user_email",
        "gps_lat", "gps_lon", "gps_timestamp",
        "selected_poi_id", "score_awarded", "answered_at",
    ])
    for answer, _question, gps_point, user in rows:
        writer.writerow([
            str(answer.id),
            str(answer.question_id),
            str(answer.user_id),
            user.email,
            gps_point.lat,
            gps_point.lon,
            gps_point.timestamp.isoformat() if gps_point.timestamp else "",
            answer.selected_poi_id,
            answer.score_awarded,
            answer.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labels.csv"},
    )


@router.get("/poi-quality")
async def poi_quality_report(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check candidate density and category diversity for each GPS point."""
    result = await db.execute(select(GpsPoint).order_by(GpsPoint.created_at.asc()))
    gps_points = result.scalars().all()

    report: list[dict] = []
    total_candidates = 0
    sparse_count = 0

    for gp in gps_points:
        pois = await get_nearby_pois(db, lat=gp.lat, lon=gp.lon)
        categories = {p["category"] for p in pois}
        count = len(pois)
        total_candidates += count
        if count < 3:
            sparse_count += 1
        report.append({
            "gps_point_id": str(gp.id),
            "lat": gp.lat,
            "lon": gp.lon,
            "candidate_count": count,
            "unique_categories": len(categories),
            "categories": sorted(categories),
        })

    return {
        "total_gps_points": len(gps_points),
        "sparse_points": sparse_count,
        "avg_candidates": round(total_candidates / max(len(gps_points), 1), 1),
        "points": report,
    }
