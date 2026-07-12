"""
Verify whether the patch from fix_pathway_ordering.py actually landed in
the live file, and if so, whether generate_execution_plan actually calls
the patched generate_engagement_pathway -- or possibly computes its own
"required_stakeholders" / step ordering independently, bypassing the
patched function entirely.

Run: docker exec agora-backend-1 python scripts/verify_patch_applied.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

with open("/app/app/services/opportunity_intelligence.py") as f:
    content = f.read()

print("=== Does the patch marker exist in the live file? ===")
print("'Bug fix (V6.0A activation cycle)' found:", "Bug fix (V6.0A activation cycle)" in content)
print()

from app.services.opportunity_intelligence import generate_engagement_pathway, generate_execution_plan, get_current_pathway

print("=== Live generate_engagement_pathway source ===")
print(inspect.getsource(generate_engagement_pathway))

print()
print("=== Live generate_execution_plan source ===")
print(inspect.getsource(generate_execution_plan))

print()
print("=== Live get_current_pathway source ===")
print(inspect.getsource(get_current_pathway))
