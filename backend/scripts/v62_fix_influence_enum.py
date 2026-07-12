"""
NDIP V6.2 -- Fix StakeholderInfluenceLevel mapping in
materialise_intelligence.py. Confirmed live: enum has LOW/MEDIUM/HIGH/CRITICAL
not VERY_HIGH.

Run: docker exec agora-backend-1 python scripts/v62_fix_influence_enum.py
"""
PATH = "/app/app/services/materialise_intelligence.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''        level_map = {
            "Very High": StakeholderInfluenceLevel.VERY_HIGH,
            "High": StakeholderInfluenceLevel.HIGH,
            "Medium": StakeholderInfluenceLevel.MEDIUM,
            "Low": StakeholderInfluenceLevel.LOW,
        }'''

new = '''        level_map = {
            "Very High": StakeholderInfluenceLevel.CRITICAL,
            "Critical": StakeholderInfluenceLevel.CRITICAL,
            "High": StakeholderInfluenceLevel.HIGH,
            "Medium": StakeholderInfluenceLevel.MEDIUM,
            "Low": StakeholderInfluenceLevel.LOW,
        }'''

count = content.count(old)
print(f"Anchor found {count} time(s).")
if count != 1:
    print("Aborting.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched: VERY_HIGH -> CRITICAL, Critical -> CRITICAL added.")
