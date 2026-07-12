"""
Follow-up check: National Pulse Executive and Election Intelligence both
have 'action' and 'reasoning' field literals but NOT 'category' -- what
are they actually doing? This determines whether there's genuine
duplicated recommendation logic to consolidate, or just a different,
narrower pattern that doesn't need the same treatment.

Run: docker exec agora-backend-1 python scripts/v614_check_partial_duplicates.py
"""
import re

for label, path in [
    ("National Pulse Executive", "/app/app/services/national_pulse_executive.py"),
    ("Election Intelligence", "/app/app/services/election_intelligence.py"),
]:
    print("=" * 70)
    print(f"  {label} -- context around 'action'/'reasoning' usage")
    print("=" * 70)
    with open(path, "r") as f:
        content = f.read()
    for keyword in ["action", "reasoning"]:
        for m in re.finditer(rf'"{keyword}"\s*:', content):
            start = max(0, m.start() - 100)
            end = min(len(content), m.end() + 100)
            print(f"\n  ...{content[start:end]}...")
