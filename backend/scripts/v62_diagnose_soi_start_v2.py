"""
Check the real current text right where the first cache-check anchor
should match, now that the import patch already landed earlier.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_soi_start_v2.py
"""
with open('/app/app/api/routes/strategic_outcome.py', 'r') as f:
    content = f.read()

idx = content.find('from app.services.opportunity_intelligence import (\n        generate_opportunity_assessments')
if idx == -1:
    print("Marker not found.")
else:
    start = max(0, idx - 50)
    print(repr(content[start:idx+250]))
