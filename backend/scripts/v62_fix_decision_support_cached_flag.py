"""
NDIP V6.2 Phase A item 1 -- Decision Support route ALREADY has working
caching (confirmed live: warm timing 0.002s vs cold 2.285s). The only
gap found is the missing _cached=True flag, present in Leadership Pack's
pattern but absent here, making the route's cache status unobservable to
any caller/report that checks that flag.

Anchor fetched fresh via live sed extraction this session.

Run: docker exec agora-backend-1 python scripts/v62_fix_decision_support_cached_flag.py
"""
PATH = "/app/app/api/routes/national_pulse.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    ck = cache_key("decision-support", f"days={days}")
    cached = get_cached(ck)
    if cached:
        return cached'''

new = '''    ck = cache_key("decision-support", f"days={days}")
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
    print("Patched successfully: Decision Support route now sets _cached=True on cache hit.")
