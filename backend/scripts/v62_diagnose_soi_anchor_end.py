"""
Check the END of strategic_outcome_dashboard's body for the mismatch,
since the start matched cleanly.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_soi_anchor_end.py
"""
with open('/app/app/api/routes/strategic_outcome.py', 'r') as f:
    content = f.read()

idx = content.find('"opportunity_dossiers": opportunity_dossiers,')
if idx == -1:
    print("Marker not found at all.")
else:
    chunk = content[idx:idx+200]
    print(repr(chunk))
