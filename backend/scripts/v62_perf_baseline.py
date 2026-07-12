"""
NDIP V6.2 Phase A -- Performance Baseline Measurement

Measures REAL, current cold-cache load times for every major executive
page's underlying route function, end to end, plus a breakdown of where
time is actually going within each -- not assumed from earlier-tonight's
profiling (which was V6.0A-era, before V6.1.1-V6.1.5's additional
stakeholder/dossier/EDE integration work).

Run: docker exec agora-backend-1 python scripts/v62_perf_baseline.py
"""
import sys
sys.path.insert(0, '/app')
import time

from app.db.database import SessionLocal
import redis

r = redis.Redis(host='redis', port=6379, decode_responses=True)
db = SessionLocal()
user = {"email": "admin@agora.rtifn.org"}


def timed_call(label, fn):
    start = time.time()
    try:
        result = fn()
        elapsed = time.time() - start
        print(f"  {elapsed:7.2f}s  {label}")
        return result, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  {elapsed:7.2f}s  {label}  -- FAILED: {type(e).__name__}: {e}")
        return None, elapsed


def clear_cache(pattern):
    keys = r.keys(pattern)
    if keys:
        r.delete(*keys)


print("=" * 70)
print("  NDIP V6.2 PERFORMANCE BASELINE -- cold cache, current codebase")
print("=" * 70)

clear_cache("agora:leadership-pack:*")
from app.api.routes.leadership_pack import leadership_pack
timed_call("Leadership Pack (days=30, cold)", lambda: leadership_pack(days=30, db=db, _=user))

clear_cache("agora:situation-room:*")
from app.api.routes.situation_room import situation_room
timed_call("Situation Room (days=30, cold)", lambda: situation_room(days=30, db=db, _=user))

from app.api.routes.strategic_outcome import strategic_outcome_dashboard
timed_call("SOI Dashboard (days=30, cold -- no cache layer on this route)", lambda: strategic_outcome_dashboard(days=30, db=db, _=user))

from app.api.routes.strategic_outcome import get_opportunity_dossier
timed_call("Opportunity Dossier #1 (cold -- no cache layer)", lambda: get_opportunity_dossier(1, db=db, _=user))
timed_call("Opportunity Dossier #5 (cold -- no cache layer)", lambda: get_opportunity_dossier(5, db=db, _=user))

from app.services.decision_support import generate_decision_support
timed_call("Decision Support (days=30, no cache layer)", lambda: generate_decision_support(db, 30))

from app.services.national_pulse_executive import generate_national_pulse_executive
timed_call("National Pulse Executive (days=30, no cache layer)", lambda: generate_national_pulse_executive(db, 30, 71, "Stable"))

from app.services.election_intelligence import generate_full_election_intelligence
timed_call("Election Intelligence (days=30, no cache layer)", lambda: generate_full_election_intelligence(db, 30))

db.close()
print()
print("=" * 70)
print("  BASELINE COMPLETE")
print("=" * 70)
