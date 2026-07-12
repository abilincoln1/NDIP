from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.database import get_db
from app.core.security import get_current_user
from app.services.analyst_engine import get_full_analyst_brief
from app.services.source_quality import get_source_quality_report, get_data_quality_report
from app.services.narrative_intelligence import generate_situation_room, generate_brief
from app.analytics.engine import compute_all_metrics

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/leadership-pack.pdf")
def export_leadership_pack_pdf(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    try:
        from app.services.pdf_export import generate_leadership_pack_pdf
        from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities

        brief = get_full_analyst_brief(db, days)
        situation = generate_situation_room(db, days)
        source_quality = get_source_quality_report(db, days)
        data_quality = get_data_quality_report(db)

        limitations = []
        if source_quality["source_count"] < 5:
            limitations.append(f"Intelligence based on {source_quality['source_count']} active sources.")
        if not limitations:
            limitations.append("No significant data quality limitations identified.")

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "executive_summary": situation["executive_summary"],
            "national_context": brief["national_context"],
            "comparative_intelligence": brief["comparative_intelligence"],
            "narrative_assessments": brief["narrative_assessments"],
            "risks": detect_all_risks(db, days),
            "opportunities": detect_all_opportunities(db, days),
            "outlook": brief["outlook"],
            "confidence_statement": {
                "summary": source_quality["summary"],
                "limitations": limitations,
            },
        }

        pdf_bytes = generate_leadership_pack_pdf(data)
        filename = f"RTIFN-Leadership-Pack-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return Response(content=f"PDF generation error: {e}", status_code=500, media_type="text/plain")


@router.get("/brief.pdf")
def export_brief_pdf(
    period: str = "weekly",
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Export Intelligence Brief as PDF."""
    try:
        from app.services.pdf_export import generate_leadership_pack_pdf
        from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities

        days_map = {"daily": 1, "weekly": 7, "monthly": 30}
        days = days_map.get(period, 7)
        brief = get_full_analyst_brief(db, days)
        situation = generate_situation_room(db, days)

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "executive_summary": situation["executive_summary"],
            "national_context": brief["national_context"],
            "comparative_intelligence": brief["comparative_intelligence"],
            "narrative_assessments": brief["narrative_assessments"][:5],
            "risks": detect_all_risks(db, days),
            "opportunities": detect_all_opportunities(db, days),
            "outlook": brief["outlook"],
            "confidence_statement": {"summary": f"{period.capitalize()} Intelligence Brief — NDIP - Powered by RTIFN", "limitations": []},
        }

        pdf_bytes = generate_leadership_pack_pdf(data)
        filename = f"RTIFN-{period}-brief-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return Response(content=f"PDF error: {e}", status_code=500, media_type="text/plain")
