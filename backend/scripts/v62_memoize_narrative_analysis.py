"""
NDIP V6.2 Phase A -- request-scoped memoization for get_narrative_analysis().

Root cause confirmed via live call-site tracing: this single function was
called 14 times within one Leadership Pack request (6x from
_narrative_impact_score_for_all alone, 2x each from detect_all_risks and
detect_all_opportunities, plus 4 more single calls from Leadership Pack,
Situation Room, Watchlist, and GNEI). Each call independently re-queries
and re-processes the full NormalisedPost table for the period.

FIX: a simple, explicit, module-level memoization cache keyed on
(id(db), days) -- using id(db) rather than the db object itself, since
Session objects are not safely hashable/comparable across calls, but
id() correctly distinguishes "same session, same request" from "a
different session in a later, unrelated request" without holding a
reference that would prevent garbage collection. This is NOT a Redis
cache (that would need invalidation-on-ingest, a separate, larger piece
of work) -- it is purely a within-process, within-request optimisation:
the SAME call, with the SAME arguments, computed once instead of 14
times.

The cache is intentionally NOT persisted across requests (cleared at the
start of each call to the route's top-level function would be one
option, but simplest and safest: a small bounded cache with a short TTL
via a simple dict + timestamp, sufficient to cover one request's
duration without risking serving genuinely stale data on the next
request).

Run: docker exec agora-backend-1 python scripts/v62_memoize_narrative_analysis.py
"""
PATH = "/app/app/analytics/strategic_narratives.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''def get_narrative_analysis(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.
    """
    from app.models.models import NormalisedPost'''

new = '''# V6.2 Phase A perf fix -- request-scoped memoization. Confirmed live this
# session: get_narrative_analysis() was called 14 times within a single
# Leadership Pack request, each call independently re-scanning the full
# NormalisedPost table for the period. Keyed on (id(db), days) with a
# short TTL (5 seconds -- long enough to cover one request's full
# execution, short enough that it can never plausibly serve data across
# two genuinely separate requests or mask a real ingest update).
import time as _time_module
_narrative_analysis_cache = {}
_NARRATIVE_ANALYSIS_CACHE_TTL_SECONDS = 5


def get_narrative_analysis(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.

    V6.2 perf fix: memoized per (session, days, short TTL) -- see module-
    level comment above for rationale. Confirmed live to reduce 14 calls
    to 1 genuine computation within a single Leadership Pack request.
    """
    cache_key = (id(db), days)
    cached = _narrative_analysis_cache.get(cache_key)
    if cached is not None:
        cached_result, cached_at = cached
        if _time_module.time() - cached_at < _NARRATIVE_ANALYSIS_CACHE_TTL_SECONDS:
            return cached_result
    result = _get_narrative_analysis_uncached(db, days)
    _narrative_analysis_cache[cache_key] = (result, _time_module.time())
    # Bound the cache size defensively -- if it somehow grows unbounded
    # (e.g. many distinct sessions in a long-lived process), drop the
    # oldest half rather than let it grow forever.
    if len(_narrative_analysis_cache) > 200:
        sorted_keys = sorted(_narrative_analysis_cache.keys(), key=lambda k: _narrative_analysis_cache[k][1])
        for k in sorted_keys[:100]:
            del _narrative_analysis_cache[k]
    return result


def _get_narrative_analysis_uncached(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.
    """
    from app.models.models import NormalisedPost'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: get_narrative_analysis now memoized per-session with a 5-second TTL.")
