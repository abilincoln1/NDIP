"""
NDIP V6.2 -- check whether generate_situation_room() (called from
narrative_intelligence.py, 2.76s) internally duplicates work that's
already memoized, or has its own genuine separate cost worth profiling
further.

Run: docker exec agora-backend-1 python scripts/v62_check_situation_room_duplication.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.narrative_intelligence import generate_situation_room
source = inspect.getsource(generate_situation_room)
print(f"Function length: {len(source)} chars")
print()
print(source[:2500])
