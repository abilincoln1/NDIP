"""
Diagnostic: find the exact discrepancy between the anchor text used in
v613_add_responsible_stakeholders.py and the real live decision_support.py.

Run: docker exec agora-backend-1 python scripts/v613_diagnose_anchor.py
"""
with open('/app/app/services/decision_support.py', 'r') as f:
    content = f.read()

idx = content.find('horizon_map = {')
if idx == -1:
    print("'horizon_map = {' not found at all in the live file.")
else:
    chunk = content[idx:idx+550]
    print("Real text at that location (repr, to reveal exact whitespace/encoding):")
    print(repr(chunk))
