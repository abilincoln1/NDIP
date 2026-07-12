"""
Diagnostic: find the exact discrepancy preventing the SOI dashboard
caching patch's function-body anchor from matching.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_soi_anchor.py
"""
with open('/app/app/api/routes/strategic_outcome.py', 'r') as f:
    content = f.read()

idx = content.find('def strategic_outcome_dashboard')
if idx == -1:
    print("Function not found at all.")
else:
    chunk = content[idx:idx+700]
    print(repr(chunk))
