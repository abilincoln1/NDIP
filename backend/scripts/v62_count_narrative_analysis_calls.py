"""
NDIP V6.2 -- Count exactly how many times get_narrative_analysis() is
called during a single Leadership Pack request, via monkey-patching to
intercept and count real calls -- not estimated from source reading.

Run: docker exec agora-backend-1 python scripts/v62_count_narrative_analysis_calls.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
import app.analytics.strategic_narratives as sn_module

call_count = [0]
original_fn = sn_module.get_narrative_analysis

def counting_wrapper(*args, **kwargs):
    call_count[0] += 1
    return original_fn(*args, **kwargs)

sn_module.get_narrative_analysis = counting_wrapper

# Also patch it in every module that already did `from ... import get_narrative_analysis`
import app.api.routes.leadership_pack as lp_module
import importlib

db = SessionLocal()
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
db.close()

print(f"get_narrative_analysis() was called {call_count[0]} time(s) during a single Leadership Pack request.")
