"""
Direct, conclusive test: does the exact literal string match the real
file content right now, byte for byte?

Run: docker exec agora-backend-1 python scripts/v62_direct_match_test.py
"""
with open('/app/app/api/routes/strategic_outcome.py', 'r') as f:
    content = f.read()

test_string = '''    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    generation_result = generate_opportunity_assessments(db, days)'''

print("Direct match count:", content.count(test_string))
print()
print("Test string repr:")
print(repr(test_string))
