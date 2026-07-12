#!/usr/bin/env python3
"""
Page load performance test for NDIP.
Tests all major API endpoints and measures response times.
"""
import sys, time, json
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.core.config import get_settings

settings = get_settings()

ENDPOINTS = [
    ("Leadership Pack (7d)",      lambda db: __import__('app.api.routes.leadership_pack', fromlist=['leadership_pack']).leadership_pack(days=7, db=db, _={})),
    ("Leadership Pack (30d)",     lambda db: __import__('app.api.routes.leadership_pack', fromlist=['leadership_pack']).leadership_pack(days=30, db=db, _={})),
    ("Situation Room (7d)",       lambda db: __import__('app.api.routes.situation_room', fromlist=['situation_room']).situation_room(days=7, db=db, _={})),
    ("National Pulse (7d)",       lambda db: __import__('app.api.routes.national_pulse', fromlist=['national_pulse']).national_pulse(days=7, db=db, _={})),
    ("Intelligence Brief (weekly)",lambda db: __import__('app.api.routes.situation_room', fromlist=['executive_brief']).executive_brief(period='weekly', db=db, _={})),
    ("Historical Overview",       lambda db: __import__('app.api.routes.historical', fromlist=['historical_overview']).historical_overview(db=db, _={})),
]

def test_endpoint(name, fn, db, runs=3):
    times = []
    cached_times = []
    first_cached = None

    for i in range(runs):
        start = time.perf_counter()
        try:
            result = fn(db)
            elapsed = (time.perf_counter() - start) * 1000
            is_cached = isinstance(result, dict) and result.get("_cached", False)
            if i == 0:
                times.append(elapsed)
            else:
                cached_times.append(elapsed)
                if first_cached is None:
                    first_cached = elapsed
        except Exception as e:
            elapsed = -1
            print(f"  ERROR on run {i+1}: {e}")

    first = times[0] if times else 0
    avg_cached = sum(cached_times) / len(cached_times) if cached_times else 0
    return first, avg_cached

print("=" * 60)
print("NDIP — PAGE LOAD PERFORMANCE TEST")
print("=" * 60)
print(f"Testing {len(ENDPOINTS)} endpoints, 3 runs each")
print(f"Run 1 = cold/compute, Runs 2-3 = cached")
print("-" * 60)

db = SessionLocal()
results = []

for name, fn in ENDPOINTS:
    print(f"Testing: {name}...")
    first, cached = test_endpoint(name, fn, db)
    results.append((name, first, cached))
    status = "✓" if first < 5000 else "⚠"
    cache_status = "✓" if cached < 100 else "~"
    print(f"  {status} First load: {first:.0f}ms  {cache_status} Cached: {cached:.0f}ms")

db.close()

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

avg_first = sum(r[1] for r in results) / len(results)
avg_cached = sum(r[2] for r in results) / len(results)

print(f"Average first load:  {avg_first:.0f}ms ({avg_first/1000:.1f}s)")
print(f"Average cached load: {avg_cached:.0f}ms ({avg_cached/1000:.2f}s)")
print(f"Cache speedup:       {avg_first/max(avg_cached,1):.0f}x faster")
print()

for name, first, cached in results:
    bar_first = "█" * min(int(first/500), 20)
    bar_cached = "█" * max(int(cached/10), 1)
    print(f"{name[:35]:<35} First: {first:>6.0f}ms {bar_first}")
    print(f"{'':35} Cache: {cached:>6.0f}ms {bar_cached}")
    print()

print("=" * 60)
rating = "Excellent" if avg_cached < 50 else "Good" if avg_cached < 200 else "Acceptable"
print(f"Overall cache performance: {rating}")
print("=" * 60)
