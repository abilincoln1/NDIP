"""
NDIP V6.2 Phase A item 1 -- SOI Dashboard caching, fixed version with the
correct blank-line-accurate anchor (confirmed via live diagnostic: a
blank line exists between "except Exception: opportunity_dossiers = []"
and "return {").

Run: docker exec agora-backend-1 python scripts/v62_add_soi_caching_v2.py
"""
PATH = "/app/app/api/routes/strategic_outcome.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    generation_result = generate_opportunity_assessments(db, days)'''

new = '''    _cache_key = cache_key("soi-dashboard", f"days={days}")
    _cached = get_cached(_cache_key)
    if _cached is not None:
        _cached["_cached"] = True
        return _cached

    from app.services.opportunity_intelligence import (
        generate_opportunity_assessments, get_top_opportunities, get_opportunity_pipeline_summary,
    )
    from app.services.stakeholder_registry import get_top_stakeholders
    from app.services.intelligence_learning import run_intelligence_learning_cycle
    generation_result = generate_opportunity_assessments(db, days)'''

count1 = content.count(old)
print(f"Cache-check insertion anchor found {count1} time(s).")
if count1 == 1:
    content = content.replace(old, new, 1)
    print("  [OK] Cache check inserted at top of function.")
else:
    print(f"  [SKIPPED] expected 1, found {count1}")

old2 = '''    except Exception:
        opportunity_dossiers = []

    return {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
        "opportunity_dossiers": opportunity_dossiers,
    }'''

new2 = '''    except Exception:
        opportunity_dossiers = []

    result = {
        "period_days": days,
        "generation_summary": generation_result,
        "top_opportunities": top_opportunities,
        "stakeholder_rankings": top_stakeholders,
        "engagement_priorities": engagement_priorities,
        "opportunity_pipeline": pipeline_summary_data,
        "strategic_value_distribution": value_counts,
        "decision_quality_metrics": learning_cycle.get("decision_quality_metrics"),
        "strategic_outcome_metrics": learning_cycle.get("strategic_outcome_metrics"),
        "platform_learning_score": learning_cycle.get("platform_learning_score"),
        "opportunity_dossiers": opportunity_dossiers,
    }
    set_cached(_cache_key, result, TTL_SOI_DASHBOARD)
    return result'''

count2 = content.count(old2)
print(f"Cache-write/return anchor found {count2} time(s).")
if count2 == 1:
    content = content.replace(old2, new2, 1)
    print("  [OK] Cache write inserted before return.")
else:
    print(f"  [SKIPPED] expected 1, found {count2}")

with open(PATH, "w") as f:
    f.write(content)
print("\nFile written.")
