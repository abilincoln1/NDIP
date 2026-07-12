#!/usr/bin/env python3
"""
Daily ingestion scheduler — Multi-Layer Intelligence Collection Framework
Layer 1 (40%): RTIFN Core Mission — Diaspora & Global Nigerian Engagement
Layer 2 (40%): National Strategic Intelligence — Security, Economy, Energy, Governance, etc.
Layer 3 (20%): Emerging Issues — dynamically generated from trend analysis
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, '/app')
os.chdir('/app')

from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal, engine, Base
from app.connectors.registry import run_ingest
from app.services.normalisation import normalise_unprocessed_batch
from app.analytics.intelligence import process_unprocessed_batch
from app.analytics.engine import compute_all_metrics
from app.models.models import AnalyticsSnapshot

# ─── Layer 1: RTIFN Core Mission Intelligence (40%) ──────────────────────────
LAYER1_QUERIES = [
    "Nigeria diaspora community UK",
    "Nigerian diaspora advocacy",
    "Africa diaspora engagement",
    "Nigeria UK community development",
    "diaspora remittance Nigeria",
    "overseas Nigerian community",
    "Nigerian diaspora investment",
    "diaspora migration policy Nigeria",
    "Nigerian community abroad civic engagement",
]

# ─── Layer 2: National Strategic Intelligence (40%) ──────────────────────────
LAYER2_QUERIES = {
    "Security": [
        "Nigeria security insecurity",
        "kidnapping banditry Nigeria",
        "terrorism Nigeria military operations",
        "violent crime police Nigeria",
    ],
    "Economy": [
        "Nigeria economy inflation",
        "cost of living Nigeria unemployment",
        "naira exchange rate economic growth Nigeria",
        "food prices household income Nigeria",
    ],
    "Energy": [
        "electricity power supply Nigeria",
        "fuel prices petrol subsidy Nigeria",
        "energy sector renewable energy Nigeria",
    ],
    "Governance": [
        "governance public policy Nigeria",
        "federal government national assembly Nigeria",
        "legislation public administration Nigeria",
    ],
    "Infrastructure": [
        "roads rail transportation Nigeria",
        "infrastructure projects housing Nigeria",
    ],
    "Education": [
        "education universities schools Nigeria",
        "student issues educational policy Nigeria",
    ],
    "Health": [
        "healthcare hospitals public health Nigeria",
        "disease outbreaks health policy Nigeria",
    ],
    "Investment": [
        "investment foreign business Nigeria",
        "entrepreneurship startup ecosystem Nigeria",
    ],
}

# Flatten Layer 2
LAYER2_FLAT = [q for queries in LAYER2_QUERIES.values() for q in queries]

# ─── Layer 3: Emerging Issues (20%) — dynamic from trend analysis ─────────────
def get_layer3_queries(db) -> list[str]:
    """Dynamically generate queries from rapidly growing topics."""
    try:
        from app.analytics.intelligence import get_trend_velocity
        velocity = get_trend_velocity(db, days=7)
        emerging = [t for t in velocity if t.get("velocity", 0) > 2.0 and t.get("trending")]
        queries = []
        for topic in emerging[:5]:
            t = topic["topic"]
            if len(t) > 3 and t not in ["nigeria", "african", "nigerian"]:
                queries.append(f"{t} Nigeria")
        return queries
    except Exception:
        return []


async def run_daily_ingest():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    print(f"\n{'='*60}")
    print(f"AGORA MULTI-LAYER INGEST — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    total_new = 0

    # Layer 1 — Core Mission
    print(f"\n{'─'*40}")
    print("LAYER 1: RTIFN Core Mission Intelligence")
    print(f"{'─'*40}")
    for query in LAYER1_QUERIES:
        try:
            result = await run_ingest(db, query)
            new = sum(s.get("new", 0) for s in result.get("platforms", {}).values())
            if new > 0:
                print(f"  ✓ '{query}': {new} new posts")
                total_new += new
        except Exception as e:
            print(f"  ✗ '{query}': {e}")

    # Layer 2 — National Strategic
    print(f"\n{'─'*40}")
    print("LAYER 2: National Strategic Intelligence")
    print(f"{'─'*40}")
    for query in LAYER2_FLAT:
        try:
            result = await run_ingest(db, query)
            new = sum(s.get("new", 0) for s in result.get("platforms", {}).values())
            if new > 0:
                print(f"  ✓ '{query}': {new} new posts")
                total_new += new
        except Exception as e:
            print(f"  ✗ '{query}': {e}")

    # Layer 3 — Emerging Issues
    print(f"\n{'─'*40}")
    print("LAYER 3: Emerging Issues Intelligence (Dynamic)")
    print(f"{'─'*40}")
    layer3 = get_layer3_queries(db)
    if layer3:
        for query in layer3:
            try:
                result = await run_ingest(db, query)
                new = sum(s.get("new", 0) for s in result.get("platforms", {}).values())
                if new > 0:
                    print(f"  ✓ '{query}' [auto]: {new} new posts")
                    total_new += new
            except Exception as e:
                print(f"  ✗ '{query}': {e}")
    else:
        print("  No emerging queries generated yet — baseline accumulating")

    print(f"\nTotal new posts: {total_new}")

    # NLP pipeline
    print("\nRunning NLP pipeline...")
    normalised = normalise_unprocessed_batch(db, 2000)
    processed = process_unprocessed_batch(db, 1000)
    print(f"Normalised: {normalised}, NLP processed: {processed}")

    # Save snapshot
    print("\nSaving analytics snapshot...")
    try:
        metrics = compute_all_metrics(db)
        snap = AnalyticsSnapshot(
            snapshot_date=now,
            engagement_index=metrics.get("engagement_index", 0),
            participation_index=metrics.get("participation_index", 0),
            growth_rate=metrics.get("growth_rate", 0),
            sentiment_score=metrics.get("sentiment_score", 0),
            topic_momentum_score=metrics.get("topic_momentum_score", 0),
            total_participants=metrics.get("total_participants", 0),
            total_engagements=metrics.get("total_engagements", 0),
            new_participants=metrics.get("new_participants_7d", 0),
        )
        db.add(snap)
        db.commit()
        print(f"Snapshot saved — Engagement: {metrics['engagement_index']:.2f}")
    except Exception as e:
        print(f"Snapshot error: {e}")
        db.rollback()

    # Weekly report Monday
    if now.weekday() == 0:
        print("\nGenerating weekly report...")
        try:
            from app.services.report_service import generate_report
            report = generate_report(db, period="weekly",
                period_start=now - timedelta(days=7), period_end=now)
            print(f"Weekly report: {report.title}")
        except Exception as e:
            print(f"Report error: {e}")

    db.close()
    print(f"\n{'='*60}")
    print("INGEST COMPLETE")
    print(f"{'='*60}\n")



async def prewarm_cache(db):
    """
    Pre-compute all intelligence results immediately after ingest.
    So the first load of the day is instant for all users.
    """
    print("\nPre-warming intelligence cache...")
    from app.services.cache import set_cached, cache_key
    from app.services.cache import TTL_LEADERSHIP_PACK, TTL_NATIONAL_PULSE, TTL_SITUATION_ROOM, TTL_BRIEF

    periods = [3, 7, 14, 30]
    warmed = 0

    for days in periods:
        # Leadership Pack
        try:
            from app.services.analyst_engine import get_full_analyst_brief
            from app.services.source_quality import get_source_quality_report, get_data_quality_report
            from app.services.narrative_intelligence import generate_situation_room
            from app.analytics.engine import compute_all_metrics
            from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities

            brief = get_full_analyst_brief(db, days)
            situation = generate_situation_room(db, days)
            source_quality = get_source_quality_report(db, days)
            data_quality = get_data_quality_report(db)
            metrics = compute_all_metrics(db, max(days, 30))
            limitations = []
            if source_quality["source_count"] < 5:
                limitations.append(f"Intelligence based on {source_quality['source_count']} active sources.")
            if not limitations:
                limitations.append("No significant data quality limitations identified.")

            lp_result = {
                "generated_at": brief["generated_at"],
                "period_days": days,
                "executive_summary": situation["executive_summary"],
                "what_matters_most": situation.get("what_matters_most", ""),
                "significant_changes": situation.get("significant_changes", []),
                "national_context": brief["national_context"],
                "narrative_assessments": brief["narrative_assessments"],
                "comparative_intelligence": brief["comparative_intelligence"],
                "diaspora_intelligence": {
                    "narrative": brief["diaspora_narrative"],
                    "assessment": next((a for a in brief["narrative_assessments"] if a["narrative"] == "Global Nigerian Engagement"), None),
                },
                "national_intelligence": {
                    "narratives": brief["national_narratives"],
                    "assessments": [a for a in brief["narrative_assessments"] if a["narrative"] in ("Economy","Security","Governance","Elections & Democracy","Infrastructure","Energy","Education","Health")],
                },
                "emerging_intelligence": {
                    "narratives": brief["emerging_narratives"],
                    "description": f"{len([n for n in brief['emerging_narratives'] if n.get('prev_count',0)>0])} narrative(s) with significant momentum detected." if brief["emerging_narratives"] else "No unusual emerging issues detected.",
                },
                "risks": detect_all_risks(db, days),
                "opportunities": detect_all_opportunities(db, days),
                "outlook": brief["outlook"],
                "confidence_statement": {
                    "overall_rating": source_quality["overall_confidence_label"],
                    "data_quality": data_quality["overall_quality"],
                    "source_coverage": f"{source_quality['source_count']} active sources",
                    "source_diversity": "Moderate" if source_quality["source_count"] >= 5 else "Limited",
                    "evidence_volume": f"{source_quality['total_records']} records analysed",
                    "processing_rate": f"{source_quality['processing_rate']}%",
                    "limitations": limitations,
                    "summary": source_quality["summary"],
                },
                "metrics": {
                    "engagement_index": metrics["engagement_index"],
                    "sentiment_score": metrics["sentiment_score"],
                    "total_participants": metrics["total_participants"],
                },
            }
            set_cached(cache_key("leadership-pack", f"days={days}"), lp_result, TTL_LEADERSHIP_PACK)
            warmed += 1
            print(f"  ✓ Leadership Pack ({days}d)")
        except Exception as e:
            print(f"  ✗ Leadership Pack ({days}d): {e}")

        # Situation Room
        try:
            from app.services.narrative_intelligence import generate_situation_room
            sr = generate_situation_room(db, days)
            sr["risks"] = detect_all_risks(db, days)
            sr["opportunities"] = detect_all_opportunities(db, days)
            set_cached(cache_key("situation-room", f"days={days}"), sr, TTL_SITUATION_ROOM)
            warmed += 1
            print(f"  ✓ Situation Room ({days}d)")
        except Exception as e:
            print(f"  ✗ Situation Room ({days}d): {e}")

        # National Pulse
        try:
            from app.services.national_pulse import compute_national_pulse
            from app.services.evidence_layer import get_platform_confidence
            pulse = compute_national_pulse(db, days)
            pulse["platform_confidence"] = get_platform_confidence(db, days)
            set_cached(cache_key("national-pulse", f"days={days}"), pulse, TTL_NATIONAL_PULSE)
            warmed += 1
            print(f"  ✓ National Pulse ({days}d)")
        except Exception as e:
            print(f"  ✗ National Pulse ({days}d): {e}")

    # Intelligence Briefs
    for period in ["daily", "weekly", "monthly"]:
        try:
            from app.services.narrative_intelligence import generate_brief
            from app.services.comparative_intelligence import get_narrative_comparisons
            from app.services.source_quality import get_source_quality_report, get_data_quality_report
            days_map = {"daily": 1, "weekly": 7, "monthly": 30}
            d = days_map[period]
            base = generate_brief(db, period, d)
            base["comparisons"] = get_narrative_comparisons(db, d)
            base["source_quality"] = get_source_quality_report(db, d)
            base["data_quality"] = get_data_quality_report(db)
            base["risks"] = detect_all_risks(db, d)
            base["opportunities"] = detect_all_opportunities(db, d)
            set_cached(cache_key("brief", f"period={period}"), base, TTL_BRIEF)
            warmed += 1
            print(f"  ✓ Intelligence Brief ({period})")
        except Exception as e:
            print(f"  ✗ Intelligence Brief ({period}): {e}")

    print(f"Cache pre-warmed: {warmed} endpoints ready")


def clear_cache():
    """Clear Redis cache after ingest so fresh data is served."""
    try:
        from app.services.cache import invalidate_all
        count = invalidate_all()
        print(f"Cache cleared: {count} keys invalidated")
    except Exception as e:
        print(f"Cache clear error (non-fatal): {e}")


if __name__ == "__main__":
    asyncio.run(run_daily_ingest())
    # V6.2 Phase A -- materialise intelligence before clearing Redis, so
    # the prewarm step that follows reads from persisted data rather than
    # recomputing everything from scratch on every request.
    _mat_db = SessionLocal()
    try:
        from app.services.materialise_intelligence import run_full_materialisation
        run_full_materialisation(_mat_db)
    except Exception as e:
        print(f"Materialisation error (non-fatal): {e}")
    finally:
        _mat_db.close()
    clear_cache()
    # Pre-warm cache synchronously
    db = SessionLocal()
    import asyncio as _asyncio
    _asyncio.run(prewarm_cache(db))
    db.close()
