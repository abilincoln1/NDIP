"""
NDIP V6.2 Phase A item 1 -- Election Intelligence route ALREADY has
working caching (confirmed via source inspection). Same gap as the
previous three surfaces: missing _cached=True flag on cache hit.

Anchor fetched fresh via live sed extraction this session.

Run: docker exec agora-backend-1 python scripts/v62_fix_election_cached_flag.py
"""
PATH = "/app/app/api/routes/national_pulse.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    ck = cache_key("election-intelligence-full", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached'''

new = '''    ck = cache_key("election-intelligence-full", f"days={days}")
    cached = get_cached(ck)
    if cached:
        cached["_cached"] = True
        return cached'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: Election Intelligence route now sets _cached=True on cache hit.")
