import sys, time
sys.path.insert(0, '/app')
from app.db.database import SessionLocal
db = SessionLocal()

from app.analytics.strategic_narratives import get_narrative_analysis
t = time.time(); n = get_narrative_analysis(db, 30)
print(f"narrative: {time.time()-t:.3f}s {len(n)} results mat={n[0].get('_from_materialised',False) if n else None}")

from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
t = time.time(); r = detect_all_risks(db, 30); o = detect_all_opportunities(db, 30)
print(f"risks+opps: {time.time()-t:.3f}s {len(r)}r {len(o)}o")

from app.analytics.engine import compute_all_metrics
t = time.time(); m = compute_all_metrics(db, 30)
print(f"metrics: {time.time()-t:.3f}s")

from app.services.source_quality import get_source_quality_report
t = time.time(); sq = get_source_quality_report(db, 30)
print(f"source_quality: {time.time()-t:.3f}s")

db.close()
