"""
Manual cache pre-warmer.
Run this any time you want to pre-compute all intelligence results.
Usage: docker exec agora-backend-1 python scripts/prewarm_cache.py
"""
import sys, asyncio
sys.path.insert(0, '/app')

from app.db.database import SessionLocal, engine, Base
Base.metadata.create_all(bind=engine)

from scripts.daily_ingest import prewarm_cache

db = SessionLocal()
print("Starting manual cache pre-warm...")
asyncio.run(prewarm_cache(db))

# V5.4-5.7 additional endpoint warming
try:
    from app.services.national_pulse_executive import generate_national_pulse_executive
    from app.services.national_pulse import compute_national_pulse
    pulse = compute_national_pulse(db, 7)
    generate_national_pulse_executive(db, 7, pulse.get("pulse_score", 67), pulse.get("pulse_label", "Stable"))
    print("  ✓ National Pulse Executive (7d)")
except Exception as e:
    print(f"  ! National Pulse Executive skipped: {e}")

try:
    from app.services.polarisation import compute_narrative_polarisation
    compute_narrative_polarisation(db, 7)
    print("  ✓ Polarisation (7d)")
except Exception as e:
    print(f"  ! Polarisation skipped: {e}")

try:
    from app.services.executive_actions import generate_executive_actions
    generate_executive_actions(db, 7)
    print("  ✓ Executive Actions (7d)")
except Exception as e:
    print(f"  ! Executive Actions skipped: {e}")

try:
    from app.services.gnei import generate_gnei_intelligence
    generate_gnei_intelligence(db, 7)
    print("  ✓ GNEI (7d)")
except Exception as e:
    print(f"  ! GNEI skipped: {e}")

try:
    from app.services.watchlist import generate_watchlist
    generate_watchlist(db, 7)
    print("  ✓ Watchlist (7d)")
except Exception as e:
    print(f"  ! Watchlist skipped: {e}")

try:
    from app.services.decision_support import generate_decision_support
    generate_decision_support(db, 7)
    print("  ✓ Decision Support (7d)")
except Exception as e:
    print(f"  ! Decision Support skipped: {e}")

try:
    from app.services.election_intelligence import generate_full_election_intelligence
    generate_full_election_intelligence(db, 30)
    print("  ✓ Election Intelligence + Sub-categories (30d)")
except Exception as e:
    print(f"  ! Election Intelligence skipped: {e}")

# V5.8 — Intelligence Learning Engine
try:
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    run_intelligence_learning_cycle(db)
    print("  ✓ Intelligence Learning Cycle (V5.8)")
except Exception as e:
    print(f"  ! Intelligence Learning Cycle skipped: {e}")

db.close()
print("Done.")
