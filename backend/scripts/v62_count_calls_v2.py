"""
NDIP V6.2 -- Count get_narrative_analysis() calls correctly this time,
using sys.settrace-based call counting (catches every call regardless of
how it was imported) rather than monkey-patching a potentially
already-bound reference.

Run: docker exec agora-backend-1 python scripts/v62_count_calls_v2.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal

call_count = [0]

def trace_calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == 'get_narrative_analysis':
        call_count[0] += 1
    return trace_calls

sys.settrace(trace_calls)

db = SessionLocal()
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
db.close()

sys.settrace(None)

print(f"get_narrative_analysis() was called {call_count[0]} time(s) during a single Leadership Pack request.")
