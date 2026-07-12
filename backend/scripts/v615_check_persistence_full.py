"""
Full version of the previous check, untruncated.

Run: docker exec agora-backend-1 python scripts/v615_check_persistence_full.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.recommendation_tracker import record_recommendation
print(inspect.getsource(record_recommendation))
