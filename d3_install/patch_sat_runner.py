"""
Patches sat_host_runner_v2.py to flush Redis after the rate limit test.
Run: docker exec ndip-backend-1 python3 /tmp/patch_sat_runner.py
"""
import os

TARGET = '/tmp/sat_host_runner_v2.py'

with open(TARGET, 'r') as f:
    c = f.read()

# Find the rate limit test and add a Redis flush after it
# Look for the line that checks rate limiting fires
old_markers = [
    "Rate limiting fires",
    "rate limit",
    "429 seen",
]

# Find the line
lines = c.split('\n')
rate_limit_line = None
for i, line in enumerate(lines):
    if '429 seen' in line or 'Rate limiting fires' in line:
        rate_limit_line = i
        print(f"Found rate limit test at line {i+1}: {line.strip()}")

if rate_limit_line is None:
    print("Could not find rate limit test line. Showing first 50 lines:")
    for i, l in enumerate(lines[:50]):
        print(f"{i+1}: {l}")
else:
    # Find the end of that test block (next blank line or next test)
    insert_after = rate_limit_line
    for i in range(rate_limit_line, min(rate_limit_line + 10, len(lines))):
        if lines[i].strip() == '' or (i > rate_limit_line and lines[i].strip().startswith('[')):
            insert_after = i - 1
            break

    flush_code = """
    # Flush Redis after rate limit test to prevent contamination of subsequent tests
    try:
        import redis as _redis
        _r = _redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
        _r.flushall()
    except Exception:
        pass
"""

    lines.insert(insert_after + 1, flush_code)
    c = '\n'.join(lines)

    with open(TARGET, 'w') as f:
        f.write(c)
    print(f"Redis flush inserted after line {insert_after + 1}")
    print("Done — re-run sat_host_runner_v2.py")
