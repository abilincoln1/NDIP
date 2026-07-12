"""
Diagnostic: reproduce the exact sequence of calls leadership_pack() makes,
in order, with the same db session, to find which call -- if any -- raises
an exception that the route's downstream try/except blocks for gnei,
strategic_importance, etc. are silently swallowing.

Run: docker exec agora-backend-1 python scripts/debug_leadership_pack.py
"""
import sys
sys.path.insert(0, '/app')
import traceback

from app.db.database import SessionLocal

db = SessionLocal()
days = 7

# Use the exact import paths the real leadership_pack.py route uses --
# checked directly against the source dumped from the live container.
try:
    import app.api.routes.leadership_pack as lp_module
    get_narrative_analysis = lp_module.get_narrative_analysis
    compute_all_metrics = lp_module.compute_all_metrics
    generate_situation_room = lp_module.generate_situation_room
    get_source_quality_report = lp_module.get_source_quality_report
    get_data_quality_report = lp_module.get_data_quality_report
    detect_all_risks = lp_module.detect_all_risks
    detect_all_opportunities = lp_module.detect_all_opportunities
    print("Imports from leadership_pack module OK")
except Exception:
    print("IMPORT FAILED:")
    traceback.print_exc()
    sys.exit(1)

try:
    narratives = get_narrative_analysis(db, days)
    print("narratives OK:", len(narratives))
except Exception:
    print("narratives FAILED:")
    traceback.print_exc()
    narratives = []

try:
    metrics = compute_all_metrics(db, max(days, 30))
    print("metrics OK")
except Exception:
    print("metrics FAILED:")
    traceback.print_exc()

try:
    situation = generate_situation_room(db, days)
    print("situation OK")
except Exception:
    print("situation FAILED:")
    traceback.print_exc()
    situation = {}

try:
    source_quality = get_source_quality_report(db, days)
    print("source_quality OK")
except Exception:
    print("source_quality FAILED:")
    traceback.print_exc()

try:
    data_quality = get_data_quality_report(db)
    print("data_quality OK")
except Exception:
    print("data_quality FAILED:")
    traceback.print_exc()

try:
    risks = detect_all_risks(db, days)
    print("risks OK:", len(risks))
except Exception:
    print("risks FAILED:")
    traceback.print_exc()

try:
    opportunities = detect_all_opportunities(db, days)
    print("opportunities OK:", len(opportunities))
except Exception:
    print("opportunities FAILED:")
    traceback.print_exc()

print("\n--- Now testing GNEI in this exact same session, after everything above ---")
try:
    from app.services.gnei import generate_gnei_intelligence
    gnei_result = generate_gnei_intelligence(db, days)
    print("gnei OK, score:", gnei_result.get("gnei_score"))
except Exception:
    print("gnei FAILED (this is the one the route silently swallows):")
    traceback.print_exc()

print("\nSession state check -- is the session still usable after all this?")
try:
    from app.models.models import StakeholderRegistry
    count = db.query(StakeholderRegistry).count()
    print("Session still usable, stakeholder count:", count)
except Exception:
    print("SESSION IS BROKEN:")
    traceback.print_exc()

db.close()
