"""
Verify which materialised read paths are actually activating during a
real Leadership Pack request, by checking the _from_materialised flag
on results.

Run: docker exec agora-backend-1 python scripts/v62_verify_materialised_active.py
"""
import sys; sys.path.insert(0, '/app')
import redis, time
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete("agora:leadership-pack:days=30")

from app.db.database import SessionLocal
db = SessionLocal()

# Test narrative analysis
from app.analytics.strategic_narratives import (
    get_narrative_analysis, _get_narrative_analysis_from_materialised
)
start = time.time()
mat = _get_narrative_analysis_from_materialised(db, 30)
print(f"Narrative materialised path: {'HIT' if mat else 'MISS'} ({time.time()-start:.3f}s)")
if mat:
    print(f"  Returned {len(mat)} narratives, first: {mat[0]['narrative']} ({mat[0]['count']} mentions)")

# Test influence
from app.services.stakeholder_influence import _get_top_influence_from_materialised
start = time.time()
inf = _get_top_influence_from_materialised(db, 10, 30)
print(f"Influence materialised path: {'HIT' if inf else 'MISS'} ({time.time()-start:.3f}s)")
if inf:
    print(f"  Returned {len(inf)} stakeholders, top: {inf[0]['name']} (composite={inf[0]['composite_influence_index']:.1f})")

# Full Leadership Pack cold timing
start = time.time()
from app.api.routes.leadership_pack import leadership_pack
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
elapsed = time.time() - start
print(f"\nLeadership Pack cold: {elapsed:.2f}s")

db.close()
