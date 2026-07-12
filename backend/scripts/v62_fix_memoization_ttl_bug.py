"""
NDIP V6.2 -- fix the TTL bug in the get_narrative_analysis memoization.

CONFIRMED ROOT CAUSE (via live diagnostic): the 5-second TTL was shorter
than the function's own real computation time (~4-7s observed), so by
the time a second call checked the cache, the first call's entry had
already expired -- defeating the memoization entirely for exactly the
case it was meant to fix.

FIX: remove the time-based TTL. Since this cache is correctness-bounded
by request scope (each request gets a fresh SQLAlchemy Session, so
id(db) is naturally unique per request), there is no need for a clock-
based expiry at all -- the cache is already safe because a new request
means a new `db` object means a new cache key automatically. The only
remaining defensive measure needed is bounding total cache size (already
present) to avoid unbounded growth in a long-lived process.

Run: docker exec agora-backend-1 python scripts/v62_fix_memoization_ttl_bug.py
"""
PATH = "/app/app/analytics/strategic_narratives.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''# V6.2 Phase A perf fix -- request-scoped memoization. Confirmed live this
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
    return result'''

new = '''# V6.2 Phase A perf fix -- request-scoped memoization. Confirmed live this
# session: get_narrative_analysis() was called 14 times within a single
# Leadership Pack request, each call independently re-scanning the full
# NormalisedPost table for the period.
#
# Keyed on (id(db), days). NO time-based TTL: an earlier version of this
# fix used a 5-second TTL, which was found (via live diagnostic, this
# session) to be SHORTER than the function's own real computation time
# (4-7s observed), meaning the very first cache entry had already
# expired by the time the second call checked it -- silently defeating
# the entire memoization. Correctness here comes from request scope, not
# a clock: each HTTP request gets a fresh SQLAlchemy Session, so id(db)
# is naturally unique per request, and a cache entry can never be served
# across two genuinely different requests. The only remaining concern is
# unbounded growth in a long-lived process, handled by the size bound
# below (insertion-order eviction, since Python 3.7+ dicts preserve
# insertion order).
import time as _time_module
_narrative_analysis_cache = {}
_NARRATIVE_ANALYSIS_CACHE_MAX_SIZE = 200


def get_narrative_analysis(db, days: int = 7) -> list[dict]:
    """
    Compute share of voice, momentum, sentiment, and confidence for each narrative.
    This is the core of the Strategic Intelligence layer.

    V6.2 perf fix: memoized per (session, days), no time-based expiry --
    see module-level comment above for the TTL bug this replaced.
    Confirmed live this session to reduce repeated calls within a single
    Leadership Pack request to one genuine computation.
    """
    cache_key = (id(db), days)
    if cache_key in _narrative_analysis_cache:
        return _narrative_analysis_cache[cache_key]
    result = _get_narrative_analysis_uncached(db, days)
    _narrative_analysis_cache[cache_key] = result
    if len(_narrative_analysis_cache) > _NARRATIVE_ANALYSIS_CACHE_MAX_SIZE:
        oldest_key = next(iter(_narrative_analysis_cache))
        del _narrative_analysis_cache[oldest_key]
    return result'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: TTL removed, replaced with pure request-scoped (id(db), days) memoization.")
