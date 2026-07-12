"""
Honest check: did the V6.1.5 patch break record_recommendation()'s
persistence, or is the 0-new-records result simply pre-existing dedup
behavior (e.g. skip if an identical recommendation already exists for
this narrative/period today)?

Run: docker exec agora-backend-1 python scripts/v615_check_persistence_dedup.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.recommendation_tracker import record_recommendation
print(inspect.getsource(record_recommendation)[:1500])
