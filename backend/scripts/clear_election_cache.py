#!/usr/bin/env python3
"""
Clear the cached Election Intelligence responses so the frontend picks up
the V5.7 election_subcategories field instead of a stale pre-V5.7 cached
response (cached before election_subcategory.py existed, or during one
of today's broken-import states).

Run: docker exec agora-backend-1 python scripts/clear_election_cache.py
"""
import sys
sys.path.insert(0, '/app')

from app.services.cache import invalidate_pattern


def main():
    print("=" * 60)
    print("  Clearing stale Election Intelligence cache")
    print("=" * 60)

    cleared = invalidate_pattern("election-intelligence-full")
    print(f"\n  Cleared {cleared} cached election-intelligence-full entr{'y' if cleared == 1 else 'ies'}.")

    if cleared == 0:
        print("  (Zero found — either already clear, or Redis is unavailable.")
        print("   If the page still shows no Electoral Discourse Breakdown after")
        print("   this, the issue is elsewhere, not stale cache.)")
    else:
        print("  Next page load for any day-window (7d/14d/30d/60d) will compute")
        print("  fresh data including the election_subcategories field.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
