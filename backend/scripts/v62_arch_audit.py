"""
Read-only architectural audit: trace every computation executed during
a cold request for Leadership Pack, Situation Room, and SOI Dashboard.
No modifications made.
"""
import sys; sys.path.insert(0, '/app')
import inspect

# Leadership Pack entry point
from app.api.routes.leadership_pack import leadership_pack
print("=== LEADERSHIP PACK SOURCE ===")
print(inspect.getsource(leadership_pack))

# Situation Room entry point
from app.services.narrative_intelligence import generate_situation_room
print("\n=== GENERATE SITUATION ROOM SOURCE ===")
print(inspect.getsource(generate_situation_room))

# SOI Dashboard entry point
from app.api.routes.strategic_outcome import strategic_outcome_dashboard
print("\n=== SOI DASHBOARD SOURCE ===")
print(inspect.getsource(strategic_outcome_dashboard))
