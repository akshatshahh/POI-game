"""Admin endpoints: GPS point import and label export."""

import csv
import io
import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Answer, GpsPoint, Question, User
from app.schemas import GpsPointBulkRequest, GpsPointBulkResponse
from app.services.poi_service import get_nearby_pois
from app.services.question_service import _lat_lon_to_h3

router = APIRouter(prefix="/admin", tags=["admin"])

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_POI_QUALITY_SCAN = 200


def _excel_safe(value: object) -> str:
    """Prefix cells that could be interpreted as formulas when opened in Excel."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


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
            h3_cell=_lat_lon_to_h3(point.lat, point.lon),
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

        gps = GpsPoint(
            lat=lat, lon=lon, timestamp=timestamp, source=source,
            h3_cell=_lat_lon_to_h3(lat, lon),
        )
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
            _excel_safe(user.email),
            gps_point.lat,
            gps_point.lon,
            gps_point.timestamp.isoformat() if gps_point.timestamp else "",
            _excel_safe(answer.selected_poi_id),
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
    include_points: bool = Query(
        False,
        description="If true, include per-point breakdown for the scanned sample.",
    ),
) -> dict:
    """Check candidate density (scans at most 200 points to limit DB load)."""
    result = await db.execute(select(GpsPoint).order_by(GpsPoint.created_at.asc()))
    gps_points = result.scalars().all()

    sample = gps_points[:MAX_POI_QUALITY_SCAN]
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
        "total_gps_points": len(gps_points),
        "scanned_points": n,
        "scan_truncated": len(gps_points) > MAX_POI_QUALITY_SCAN,
        "sparse_points_in_sample": sparse_count,
        "avg_candidates_in_sample": round(total_candidates / max(n, 1), 1),
        "points": report,
    }
