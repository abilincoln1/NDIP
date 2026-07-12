"""
Diagnostic: find the exact discrepancy preventing the V6.1.5 anchor from
matching the live decision_support.py.

Run: docker exec agora-backend-1 python scripts/v615_diagnose_anchor.py
"""
with open('/app/app/services/decision_support.py', 'r') as f:
    content = f.read()

idx = content.find('NARRATIVE_SECTOR_MAP = {')
if idx == -1:
    print("'NARRATIVE_SECTOR_MAP = {' not found at all -- may already be patched, or text differs more than expected.")
else:
    start = max(0, idx - 50)
    end = min(len(content), idx + 1700)
    print(repr(content[start:end]))
