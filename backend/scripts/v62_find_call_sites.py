"""
NDIP V6.2 -- find the exact call sites responsible for all 14 calls to
get_narrative_analysis() in a single Leadership Pack request, by
capturing the calling frame's function name for each call.

Run: docker exec agora-backend-1 python scripts/v62_find_call_sites.py
"""
import sys
sys.path.insert(0, '/app')

import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete("agora:leadership-pack:days=30")

call_sites = []

def trace_calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == 'get_narrative_analysis':
        caller = frame.f_back
        caller_name = caller.f_code.co_name if caller else "?"
        caller_file = caller.f_code.co_filename.split("/")[-1] if caller else "?"
        call_sites.append(f"{caller_file}:{caller_name}")
    return trace_calls

sys.settrace(trace_calls)
from app.db.database import SessionLocal
db = SessionLocal()
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
db.close()
sys.settrace(None)

print(f"Total calls: {len(call_sites)}")
print()
from collections import Counter
for site, count in Counter(call_sites).most_common():
    print(f"  {count}x  called from {site}")
