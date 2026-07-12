"""
Direct confirmation: did the TTL-removal patch actually apply to the
live file? Check for the literal absence of the old TTL variable and
presence of the new logic.

Run: docker exec agora-backend-1 python scripts/v62_confirm_ttl_removed.py
"""
with open('/app/app/analytics/strategic_narratives.py', 'r') as f:
    content = f.read()

print("Old TTL constant still present:", "_NARRATIVE_ANALYSIS_CACHE_TTL_SECONDS" in content)
print("New max-size constant present:", "_NARRATIVE_ANALYSIS_CACHE_MAX_SIZE" in content)
print("New simple 'if cache_key in' check present:", "if cache_key in _narrative_analysis_cache:" in content)
