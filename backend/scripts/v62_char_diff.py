"""
Character-by-character diff between my test string and the real file's
content at the same logical location, to find the exact byte that
differs.

Run: docker exec agora-backend-1 python scripts/v62_char_diff.py
"""
with open('/app/app/api/routes/strategic_outcome.py', 'r') as f:
    content = f.read()

# Locate via a shorter, confirmed-matching anchor, then grab the real text after it
anchor = 'def strategic_outcome_dashboard('
idx = content.find(anchor)
real_chunk = content[idx:idx+700]

test_string = '''def strategic_outcome_dashboard(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Phase N: the consolidated executive dashboard combining everything
    V6.0 added \u2014 top opportunities, stakeholder rankings, the opportunity
    pipeline, engagement priorities, the outcome tracker's strategic
    metrics, and decision quality. Generates fresh opportunity assessments
    from current discourse before returning, so the dashboard always
    reflects up-to-date signal detection rather than only previously
    promoted opportunities.
    """
    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    generation_result = generate_opportunity_assessments(db, days)'''

print(f"real_chunk length: {len(real_chunk)}")
print(f"test_string length: {len(test_string)}")
print()
for i, (a, b) in enumerate(zip(real_chunk, test_string)):
    if a != b:
        print(f"First mismatch at position {i}:")
        print(f"  real: {real_chunk[max(0,i-30):i+30]!r}")
        print(f"  test: {test_string[max(0,i-30):i+30]!r}")
        break
else:
    print("No character mismatch found within the overlapping length -- one string is a prefix of the other, or they're identical up to the shorter length.")
