"""
NDIP V6.1.4 Phase A pre-audit -- before designing the Unified
Recommendation Engine, confirm which of the spec's listed modules
ACTUALLY generate their own recommendation-shaped data structures right
now, versus which ones either (a) already just consume Decision
Support's output, or (b) don't produce anything recommendation-shaped at
all (e.g. National Pulse's "key findings" are narrative descriptions,
not action recommendations).

This determines real scope: refactoring a module that has no
recommendation logic of its own is not meaningful work.

Run: docker exec agora-backend-1 python scripts/v614_audit_recommendation_sources.py
"""
import sys
sys.path.insert(0, '/app')
import subprocess

print("=" * 70)
print("  Searching codebase for recommendation-shaped dict construction")
print("  (i.e. dicts with 'category' + 'action' + 'reasoning' keys together,")
print("   the actual shape Decision Support uses -- not just any dict)")
print("=" * 70)

result = subprocess.run(
    ["grep", "-rl", "-E", '"category":\\s*"(ENGAGE|MONITOR|ESCALATE|PREPARE|ACT|INVESTIGATE)"', "/app/app/"],
    capture_output=True, text=True
)
files = [f for f in result.stdout.strip().split("\n") if f and "__pycache__" not in f]
print(f"\nFiles containing recommendation-category dict literals: {len(files)}")
for f in files:
    print(f"  {f}")

print()
print("=" * 70)
print("  Checking each spec-listed module for its OWN recommendation generation")
print("=" * 70)

modules_to_check = [
    ("Leadership Pack", "/app/app/api/routes/leadership_pack.py"),
    ("Situation Room", "/app/app/api/routes/situation_room.py"),
    ("National Pulse Executive", "/app/app/services/national_pulse_executive.py"),
    ("Election Intelligence", "/app/app/services/election_intelligence.py"),
    ("GNEI", "/app/app/services/gnei.py"),
    ("Entity Intelligence", "/app/app/services/entity_influence.py"),
    ("Decision Support Engine", "/app/app/services/decision_support.py"),
]

for label, path in modules_to_check:
    try:
        with open(path, "r") as f:
            content = f.read()
        has_category = '"category"' in content
        has_action = '"action"' in content
        has_reasoning = '"reasoning"' in content
        calls_decision_support = "generate_decision_support" in content or "decision_support" in content.lower()
        print(f"\n  {label} ({path}):")
        print(f"    Has own 'category' field literal: {has_category}")
        print(f"    Has own 'action' field literal: {has_action}")
        print(f"    Has own 'reasoning' field literal: {has_reasoning}")
        print(f"    References decision_support module: {calls_decision_support}")
    except FileNotFoundError:
        print(f"\n  {label}: FILE NOT FOUND at {path} -- module/path name may be wrong, needs verification")
