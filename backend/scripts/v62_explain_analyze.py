"""
NDIP V6.2 Phase A -- Database Investigation via EXPLAIN ANALYZE

Connects directly to Postgres and runs EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
on every significant query pattern identified from the slow-function profiling
done earlier this session. Queries extracted from real SQLAlchemy ORM calls
by inspecting the compiled SQL, not assumed.

Run: docker exec agora-backend-1 python scripts/v62_explain_analyze.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()


def explain(label, sql, params=None):
    print(f"\n{'='*70}")
    print(f"  QUERY: {label}")
    print(f"{'='*70}")
    try:
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}"
        result = db.execute(text(explain_sql), params or {})
        for row in result:
            print(row[0])
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        db.rollback()


from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc)
days = 30
since = now - timedelta(days=days)
prev_since = since - timedelta(days=days)

# ── 1. NormalisedPost full scan -- the core of get_narrative_analysis ──────────
explain("NormalisedPost -- current period scan (narrative analysis)",
    """SELECT id, text, published_at, source_platform, narrative_category, sentiment_score
       FROM normalised_posts
       WHERE published_at >= :since
         AND nlp_processed = true
         AND text IS NOT NULL""",
    {"since": since})

explain("NormalisedPost -- previous period scan (momentum calculation)",
    """SELECT id, text, published_at, source_platform, narrative_category, sentiment_score
       FROM normalised_posts
       WHERE published_at >= :prev_since
         AND published_at < :since
         AND nlp_processed = true
         AND text IS NOT NULL""",
    {"since": since, "prev_since": prev_since})

# ── 2. StakeholderRegistry scan -- mentions computation ────────────────────────
explain("StakeholderRegistry -- active stakeholders with aliases",
    """SELECT id, name, aliases_json, category, sector, stakeholder_type, is_active
       FROM stakeholder_registry
       WHERE is_active = true""")

# ── 3. OpportunityAlignmentScore -- the unbounded table ────────────────────────
explain("OpportunityAlignmentScore -- all rows for opportunity 5",
    """SELECT *
       FROM opportunity_alignment_scores
       WHERE opportunity_id = :opp_id
       ORDER BY id DESC""",
    {"opp_id": 5})

explain("OpportunityAlignmentScore -- latest per stakeholder (should be indexed)",
    """SELECT DISTINCT ON (stakeholder_id) *
       FROM opportunity_alignment_scores
       WHERE opportunity_id = :opp_id
       ORDER BY stakeholder_id, id DESC""",
    {"opp_id": 5})

# ── 4. RecommendationRecord -- dedup check on each insert ─────────────────────
explain("RecommendationRecord -- dedup guard query",
    """SELECT id FROM recommendation_records
       WHERE module = 'decision_support'
         AND recommendation_category = 'ENGAGE'
         AND narrative IS NULL
         AND status = 'OPEN'
         AND created_at >= :cutoff
       ORDER BY created_at DESC
       LIMIT 1""",
    {"cutoff": now - timedelta(hours=24)})

# ── 5. EntityMention -- top entities query ─────────────────────────────────────
explain("EntityMention -- top entities for period",
    """SELECT entity_name, entity_type, COUNT(*) as mention_count
       FROM entity_mentions
       WHERE mentioned_at >= :since
       GROUP BY entity_name, entity_type
       ORDER BY mention_count DESC
       LIMIT 10""",
    {"since": since})

# ── 6. StakeholderRelationship -- relationship lookup ─────────────────────────
explain("StakeholderRelationship -- active relationships for stakeholder",
    """SELECT *
       FROM stakeholder_relationships
       WHERE (from_stakeholder_id = :sid OR to_stakeholder_id = :sid)
         AND is_active = true""",
    {"sid": 18})

db.close()
print(f"\n{'='*70}")
print("  EXPLAIN ANALYZE COMPLETE")
print(f"{'='*70}")
