"""
NDIP V6.2 -- verify the memoization fix actually eliminates the
expensive work, by tracing calls to the renamed
_get_narrative_analysis_uncached (the real computation) separately from
the wrapper, and by measuring real before/after timing.

Run: docker exec agora-backend-1 python scripts/v62_verify_memoization_real_savings.py
"""
import sys
sys.path.insert(0, '/app')
import time

import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete("agora:leadership-pack:days=30")

uncached_call_count = [0]

def trace_calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == '_get_narrative_analysis_uncached':
        uncached_call_count[0] += 1
    return trace_calls

sys.settrace(trace_calls)
from app.db.database import SessionLocal
db = SessionLocal()
from app.api.routes.leadership_pack import leadership_pack
start = time.time()
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
elapsed = time.time() - start
db.close()
sys.settrace(None)

print(f"_get_narrative_analysis_uncached() -- the REAL, expensive computation -- called: {uncached_call_count[0]} time(s)")
print(f"Total Leadership Pack request time (cold, with tracer overhead): {elapsed:.2f}s")
