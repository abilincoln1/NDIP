"""
NDIP V8 — Daily Intelligence Snapshot Worker — uses :param bindparam style
"""
import sys
sys.path.insert(0, '/app')

import json
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import text
from app.db.database import SessionLocal


def take_snapshot(db):
    today = date.today()
    print(f"Taking snapshot for {today}...")

    # Narratives
    narrative_data = []
    try:
        rows = db.execute(text(
            "SELECT narrative, SUM(mention_count) as tm, AVG(sentiment_avg) as sa, AVG(velocity) as av "
            "FROM narrative_trends WHERE date_bucket > NOW() - INTERVAL '48 hours' "
            "GROUP BY narrative ORDER BY tm DESC LIMIT 11"
        )).fetchall()
        narrative_data = [{"narrative": r.narrative, "mention_count": int(r.tm or 0),
            "sentiment_score": round(float(r.sa or 0), 3), "velocity": round(float(r.av or 0), 2)}
            for r in rows]
        print(f"  OK Narratives: {len(narrative_data)}")
    except Exception as e:
        db.rollback(); print(f"  WARN narratives: {e}")

    # Metrics
    engagement_index = sentiment_score = None
    try:
        row = db.execute(text(
            "SELECT engagement_index, sentiment_score FROM analytics_snapshots ORDER BY snapshot_date DESC LIMIT 1"
        )).fetchone()
        if row:
            engagement_index = float(row.engagement_index or 0)
            sentiment_score = float(row.sentiment_score or 0)
        print(f"  OK Engagement: {engagement_index}, Sentiment: {sentiment_score}")
    except Exception as e:
        db.rollback(); print(f"  WARN metrics: {e}")

    # Stakeholders
    top_stakeholders = []
    try:
        rows = db.execute(text(
            "SELECT sip.stakeholder_id, sr.name, sip.composite_index, sip.influence_level "
            "FROM stakeholder_influence_profiles sip "
            "JOIN stakeholder_registry sr ON sr.id = sip.stakeholder_id "
            "ORDER BY sip.composite_index DESC LIMIT 10"
        )).fetchall()
        top_stakeholders = [{"id": r.stakeholder_id, "name": r.name,
            "composite_index": float(r.composite_index or 0), "level": r.influence_level}
            for r in rows]
        print(f"  OK Stakeholders: {len(top_stakeholders)}")
    except Exception as e:
        db.rollback(); print(f"  WARN stakeholders: {e}")

    # Opportunities
    top_opportunities = []
    try:
        rows = db.execute(text(
            "SELECT title, confidence, probability_of_success, status "
            "FROM opportunity_assessments ORDER BY probability_of_success DESC NULLS LAST LIMIT 5"
        )).fetchall()
        top_opportunities = [{"title": r.title, "confidence": r.confidence,
            "probability": float(r.probability_of_success or 0), "status": r.status}
            for r in rows]
        print(f"  OK Opportunities: {len(top_opportunities)}")
    except Exception as e:
        db.rollback(); print(f"  WARN opportunities: {e}")

    confidence_label = "Medium"

    # Write snapshot using :param style — no % characters
    try:
        db.execute(text(
            "INSERT INTO daily_intelligence_snapshots ("
            "snapshot_date, snapshot_type, narrative_data, engagement_index, sentiment_score, "
            "watchlist_data, watchlist_critical_count, watchlist_high_count, "
            "top_stakeholders, top_opportunities, confidence_label, created_at"
            ") VALUES ("
            ":sdate, 'daily', cast(:ndata as jsonb), :eidx, :sscore, "
            "cast(:wdata as jsonb), 0, 0, "
            "cast(:tstk as jsonb), cast(:topps as jsonb), :conf, NOW()"
            ") ON CONFLICT (snapshot_date, snapshot_type) DO UPDATE SET "
            "narrative_data=cast(excluded.narrative_data as jsonb), "
            "engagement_index=excluded.engagement_index, "
            "sentiment_score=excluded.sentiment_score, "
            "top_stakeholders=cast(excluded.top_stakeholders as jsonb), "
            "top_opportunities=cast(excluded.top_opportunities as jsonb), "
            "created_at=NOW()"
        ), {
            "sdate": today,
            "ndata": json.dumps(narrative_data),
            "eidx": engagement_index,
            "sscore": sentiment_score,
            "wdata": json.dumps([]),
            "tstk": json.dumps(top_stakeholders),
            "topps": json.dumps(top_opportunities),
            "conf": confidence_label,
        })
        db.commit()
        print(f"  OK Snapshot saved for {today}")
    except Exception as e:
        db.rollback()
        print(f"  FAIL Save snapshot: {e}")
        raise


def run():
    print("NDIP V8 — Daily Intelligence Snapshot")
    print("=" * 50)
    db = SessionLocal()
    try:
        take_snapshot(db)
    finally:
        db.close()
    print("=" * 50)
    print("Snapshot complete.")


if __name__ == "__main__":
    run()
