"""
Read-only final architecture verification.
Traces execution order and timing for all three dashboards.
No modifications.
"""
import sys, time
sys.path.insert(0, '/app')
import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)

from app.db.database import SessionLocal

# Patch to record call order and timing
call_log = []
original_time = time.time

def make_tracer(name):
    def trace(frame, event, arg):
        fns_to_watch = {
            'get_narrative_analysis', '_get_narrative_analysis_from_materialised',
            '_get_narrative_analysis_uncached', 'compute_all_metrics',
            'generate_situation_room', 'get_source_quality_report',
            'get_data_quality_report', 'detect_all_risks', 'detect_all_opportunities',
            'generate_watchlist', 'generate_gnei_intelligence',
            'get_top_influence_stakeholders', '_get_top_influence_from_materialised',
            'get_top_stakeholders', 'get_top_opportunities',
            'run_intelligence_learning_cycle', 'generate_opportunity_assessments',
            'get_top_entities', 'get_sentiment_trends', 'get_emerging_topics',
            'get_source_quality_report', 'get_emerging_stakeholders',
            'generate_opportunity_dossier', 'score_all_narratives',
            'record_recommendation',
        }
        if event == 'call' and frame.f_code.co_name in fns_to_watch:
            call_log.append((name, frame.f_code.co_name, time.time()))
        return trace
    return trace

import sys as _sys

# ── Leadership Pack cold ──────────────────────────────────────────────────────
r.delete(*[k for k in r.keys("agora:*")] or ["__dummy__"])
call_log.clear()
db = SessionLocal()
_sys.settrace(make_tracer("LP"))
from app.api.routes.leadership_pack import leadership_pack
t0 = time.time()
lp = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
lp_time = time.time() - t0
_sys.settrace(None)
db.close()

lp_log = [(fn, t - t0) for (dash, fn, t) in call_log if dash == "LP"]

print("="*70)
print("  LEADERSHIP PACK — CALL ORDER AND TIMING (cold cache)")
print(f"  Total: {lp_time:.2f}s")
print("="*70)
from collections import Counter
counts = Counter(fn for fn, _ in lp_log)
for fn, t in lp_log:
    marker = f" [x{counts[fn]}]" if counts[fn] > 1 else ""
    print(f"  {t:6.3f}s  {fn}{marker}")

# ── Situation Room cold ───────────────────────────────────────────────────────
r.delete(*[k for k in r.keys("agora:*")] or ["__dummy__"])
call_log.clear()
db = SessionLocal()
_sys.settrace(make_tracer("SR"))
from app.services.narrative_intelligence import generate_situation_room
t0 = time.time()
sr = generate_situation_room(db, days=30)
sr_time = time.time() - t0
_sys.settrace(None)
db.close()

sr_log = [(fn, t - t0) for (dash, fn, t) in call_log if dash == "SR"]
print("\n" + "="*70)
print("  SITUATION ROOM — CALL ORDER AND TIMING (cold cache)")
print(f"  Total: {sr_time:.2f}s")
print("="*70)
counts = Counter(fn for fn, _ in sr_log)
for fn, t in sr_log:
    marker = f" [x{counts[fn]}]" if counts[fn] > 1 else ""
    print(f"  {t:6.3f}s  {fn}{marker}")

# ── SOI Dashboard cold ────────────────────────────────────────────────────────
r.delete(*[k for k in r.keys("agora:*")] or ["__dummy__"])
call_log.clear()
db = SessionLocal()
_sys.settrace(make_tracer("SOI"))
from app.api.routes.strategic_outcome import strategic_outcome_dashboard
t0 = time.time()
soi = strategic_outcome_dashboard(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
soi_time = time.time() - t0
_sys.settrace(None)
db.close()

soi_log = [(fn, t - t0) for (dash, fn, t) in call_log if dash == "SOI"]
print("\n" + "="*70)
print("  SOI DASHBOARD — CALL ORDER AND TIMING (cold cache)")
print(f"  Total: {soi_time:.2f}s")
print("="*70)
counts = Counter(fn for fn, _ in soi_log)
for fn, t in soi_log:
    marker = f" [x{counts[fn]}]" if counts[fn] > 1 else ""
    print(f"  {t:6.3f}s  {fn}{marker}")

print("\nDone.")
