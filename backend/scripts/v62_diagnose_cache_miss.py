"""
NDIP V6.2 -- diagnose why 3 calls with the identical (id(db), days=30) key
still all missed the cache. Check id(db) stability and cache dict state
directly across the 3 real calls.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_cache_miss.py
"""
import sys
sys.path.insert(0, '/app')

import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete("agora:leadership-pack:days=30")

from app.db.database import SessionLocal
db = SessionLocal()
print(f"db session id at top level: {id(db)}")

import app.analytics.strategic_narratives as sn

call_info = []

def trace_calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == '_get_narrative_analysis_uncached':
        local_db = frame.f_locals.get('db')
        call_info.append({
            "db_id": id(local_db),
            "cache_size_before": len(sn._narrative_analysis_cache),
            "cache_keys": list(sn._narrative_analysis_cache.keys()),
        })
    return trace_calls

sys.settrace(trace_calls)
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
sys.settrace(None)
db.close()

print(f"\nReal computation calls: {len(call_info)}")
for i, info in enumerate(call_info):
    print(f"  Call {i+1}: db_id={info['db_id']}, cache_size_before={info['cache_size_before']}, cache_keys_before={info['cache_keys']}")
