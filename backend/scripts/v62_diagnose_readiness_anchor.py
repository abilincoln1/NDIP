"""
Diagnostic: find why the compute_opportunity_readiness signature patch
was skipped, before the now-broken call-site change causes a real error.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_readiness_anchor.py
"""
with open('/app/app/services/opportunity_intelligence.py', 'r') as f:
    content = f.read()

idx = content.find('def compute_opportunity_readiness')
if idx == -1:
    print("Function not found at all.")
else:
    print(repr(content[idx:idx+600]))
