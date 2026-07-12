"""
Diagnostic script: trace the actual intermediate values inside
_compute_momentum_score for the Rural Electrification Agency (stakeholder
id 18) to understand why momentum_score is returning exactly 100.0 for
every stakeholder regardless of their real mention volume.

Run: docker exec agora-backend-1 python scripts/debug_momentum.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import NormalisedPost, StakeholderRegistry
from app.services.stakeholder_registry import _load_active_registry_aliases, match_stakeholders_in_text
from datetime import datetime, timezone, timedelta

db = SessionLocal()
days = 30
since = datetime.now(timezone.utc) - timedelta(days=days)
prev_since = since - timedelta(days=days)
print("since:", since)
print("prev_since:", prev_since)

aliases = _load_active_registry_aliases(db, StakeholderRegistry)
stakeholder_id = 18
print("\nstakeholder_id in aliases:", stakeholder_id in aliases)
single_alias_set = {stakeholder_id: aliases[stakeholder_id]}
print("aliases for REA:", aliases[stakeholder_id])

current_posts = db.query(NormalisedPost.text).filter(
    NormalisedPost.published_at >= since, NormalisedPost.text.isnot(None)
).all()
prev_posts = db.query(NormalisedPost.text).filter(
    NormalisedPost.published_at >= prev_since, NormalisedPost.published_at < since,
    NormalisedPost.text.isnot(None),
).all()
print("\ncurrent_posts total (all stakeholders, this period):", len(current_posts))
print("prev_posts total (all stakeholders, prior period):", len(prev_posts))

current_count = sum(1 for (text,) in current_posts if match_stakeholders_in_text(text, single_alias_set))
prev_count = sum(1 for (text,) in prev_posts if match_stakeholders_in_text(text, single_alias_set))
print("\ncurrent_count (REA mentions, this period):", current_count)
print("prev_count (REA mentions, prior period):", prev_count)

if prev_count == 0:
    result = 50.0 if current_count > 0 else 0.0
    print("\n>>> Hit zero-prev branch. Result:", result)
else:
    pct_change = ((current_count - prev_count) / prev_count) * 100
    result = max(0.0, min(100.0, 50.0 + pct_change / 2))
    print("\npct_change:", pct_change)
    print(">>> Result:", result)

db.close()
