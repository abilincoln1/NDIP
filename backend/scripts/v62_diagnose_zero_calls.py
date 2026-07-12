"""
NDIP V6.2 -- Diagnose why the call-tracer found 0 calls. Two hypotheses:
(1) the Leadership Pack cache was not actually empty for this run, so it
returned a cached result without computing anything; (2) the trace
mechanism itself has a real bug.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_zero_calls.py
"""
import sys
sys.path.insert(0, '/app')

import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)

keys = r.keys("agora:leadership-pack:*")
print(f"Current Leadership Pack cache keys: {keys}")
for k in keys:
    ttl = r.ttl(k)
    print(f"  {k}: TTL={ttl}s")

# Clear and retry the trace, explicitly confirming cache state before and after
for k in keys:
    r.delete(k)
print(f"\nCleared {len(keys)} cache key(s). Re-checking...")
keys_after = r.keys("agora:leadership-pack:*")
print(f"Keys remaining after clear: {keys_after}")

# Now trace again, with cache confirmed empty
call_count = [0]
def trace_calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == 'get_narrative_analysis':
        call_count[0] += 1
    return trace_calls

sys.settrace(trace_calls)
from app.db.database import SessionLocal
db = SessionLocal()
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
db.close()
sys.settrace(None)

print(f"\nget_narrative_analysis() call count (cache confirmed cleared first): {call_count[0]}")
print(f"Result has '_cached' flag: {result.get('_cached', False)}")
