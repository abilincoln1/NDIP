from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Report
from app.schemas.schemas import ReportGenerateRequest, ReportOut
from app.services.report_service import generate_report
from app.core.security import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    valid_periods = {"weekly", "monthly", "custom"}
    if payload.period not in valid_periods:
        raise HTTPException(400, f"period must be one of: {', '.join(valid_periods)}")

    report = generate_report(
        db,
        period=payload.period,
        period_start=payload.period_start,
        period_end=payload.period_end,
        title=payload.title,
    )
    return report


@router.get("", response_model=list[ReportOut])
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    return report
