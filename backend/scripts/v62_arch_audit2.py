"""Read-only: get sources of key called functions for dependency tracing."""
import sys; sys.path.insert(0, '/app')
import inspect

from app.services.watchlist import generate_watchlist
print("=== GENERATE_WATCHLIST ===")
src = inspect.getsource(generate_watchlist)
print(src[:3000])

from app.services.stakeholder_influence import get_top_influence_stakeholders
print("\n=== GET_TOP_INFLUENCE_STAKEHOLDERS (first 40 lines) ===")
lines = inspect.getsource(get_top_influence_stakeholders).split('\n')
print('\n'.join(lines[:40]))

from app.services.opportunity_intelligence import generate_opportunity_assessments
print("\n=== GENERATE_OPPORTUNITY_ASSESSMENTS (first 40 lines) ===")
lines = inspect.getsource(generate_opportunity_assessments).split('\n')
print('\n'.join(lines[:40]))

from app.analytics.strategic_narratives import get_narrative_analysis
print("\n=== GET_NARRATIVE_ANALYSIS ===")
print(inspect.getsource(get_narrative_analysis))

from app.services.gnei import generate_gnei_intelligence
print("\n=== GENERATE_GNEI_INTELLIGENCE (first 30 lines) ===")
lines = inspect.getsource(generate_gnei_intelligence).split('\n')
print('\n'.join(lines[:30]))
