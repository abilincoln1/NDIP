"""
Both the start and end of the function body matched individually --
check the middle section (around the dossier loop / try-except) for the
real discrepancy.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_soi_middle.py
"""
with open('/app/app/api/routes/strategic_outcome.py', 'r') as f:
    content = f.read()

idx = content.find('opportunity_dossiers = []\n    try:')
if idx == -1:
    print("Marker 'opportunity_dossiers = []\\n    try:' not found -- checking alternate spacing")
    idx2 = content.find('opportunity_dossiers = []')
    if idx2 != -1:
        print(repr(content[idx2:idx2+150]))
else:
    print(repr(content[idx:idx+1400]))
