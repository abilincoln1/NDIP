"""
Fix the V5.6 dead-code bug: 'return { ... }' must become 'result = { ... }'
so that the enrichment call and final 'return result' are actually reached.
"""
path = '/app/app/services/decision_support.py'
lines = open(path).readlines()

# Line 397 (index 396) should be "    return {"
# We need to change it to "    result = {"
target_idx = None
for i, line in enumerate(lines):
    if line.strip() == "return {" and i > 380 and i < 410:
        target_idx = i
        break

if target_idx is None:
    print("ERROR: could not find target line 'return {' in expected range")
else:
    old_line = lines[target_idx]
    lines[target_idx] = old_line.replace("return {", "result = {")
    open(path, 'w').writelines(lines)
    print(f"Fixed line {target_idx + 1}: changed 'return {{' to 'result = {{'")
    print(f"Old: {old_line.rstrip()}")
    print(f"New: {lines[target_idx].rstrip()}")
