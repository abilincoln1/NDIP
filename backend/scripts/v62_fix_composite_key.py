"""
Fix: materialise_intelligence.py used scores.get("composite_influence_index")
but the real key is "composite_index". Also fix the same typo in the
materialised read path helper in stakeholder_influence.py.

Run: docker exec agora-backend-1 python scripts/v62_fix_composite_key.py
"""

# Fix 1: materialise_intelligence.py -- write correct composite_index
PATH1 = "/app/app/services/materialise_intelligence.py"
with open(PATH1, "r") as f:
    c = f.read()

old1 = 'composite_index=scores.get("composite_influence_index", 0.0),'
new1 = 'composite_index=scores.get("composite_index", 0.0),'
count1 = c.count(old1)
print(f"[materialise] composite_influence_index anchor: {count1}")
if count1 == 1:
    c = c.replace(old1, new1, 1)
    with open(PATH1, "w") as f:
        f.write(c)
    print("[materialise] Fixed: now uses composite_index key.")
else:
    print("[materialise] SKIPPED")

# Fix 2: stakeholder_influence.py -- read path uses composite_influence_index too
PATH2 = "/app/app/services/stakeholder_influence.py"
with open(PATH2, "r") as f:
    c2 = f.read()

old2 = '"composite_influence_index": profile.composite_index,'
new2 = '"composite_index": profile.composite_index,'
count2 = c2.count(old2)
print(f"[influence read] composite_influence_index anchor: {count2}")
if count2 == 1:
    c2 = c2.replace(old2, new2, 1)
    with open(PATH2, "w") as f:
        f.write(c2)
    print("[influence read] Fixed: return key now composite_index.")
else:
    print("[influence read] SKIPPED")
