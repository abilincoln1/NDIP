"""
NDIP V6.2 -- check whether the 3 real computations (down from 14) are
explained by genuinely different `days` arguments being passed to
get_narrative_analysis() by different callers within the same request.

Run: docker exec agora-backend-1 python scripts/v62_check_days_variance.py
"""
import sys
sys.path.insert(0, '/app')

import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete("agora:leadership-pack:days=30")

calls_with_args = []

def trace_calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == '_get_narrative_analysis_uncached':
        local_days = frame.f_locals.get('days', '?')
        caller = frame.f_back
        caller_name = caller.f_code.co_name if caller else "?"
        calls_with_args.append((caller_name, local_days))
    return trace_calls

sys.settrace(trace_calls)
from app.db.database import SessionLocal
db = SessionLocal()
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
db.close()
sys.settrace(None)

print(f"Real computations: {len(calls_with_args)}")
for caller, days_val in calls_with_args:
    print(f"  called from {caller}, days={days_val}")
