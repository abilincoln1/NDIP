"""
Temporarily raises rate limits in health_v2.py for SAT testing.
Run: docker exec ndip-backend-1 python3 /tmp/raise_sat_limits.py
"""
TARGET = '/app/app/api/routes/health_v2.py'

with open(TARGET, 'r') as f:
    c = f.read()

# Raise all limits to 500 for SAT run
import re

# Replace the RATE_LIMITS dict values
c = re.sub(r'"strict":\s*\(\d+,\s*60\)', '"strict": (500, 60)', c)
c = re.sub(r'"unauthenticated":\s*\(\d+,\s*60\)', '"unauthenticated": (500, 60)', c)
c = re.sub(r'"authenticated":\s*\(\d+,\s*60\)', '"authenticated": (500, 60)', c)

with open(TARGET, 'w') as f:
    f.write(c)

# Verify
import re
matches = re.findall(r'"(strict|unauthenticated|authenticated)":\s*\(\d+,\s*60\)', c)
for m in re.findall(r'"(?:strict|unauthenticated|authenticated)":\s*\(\d+,\s*60\)', c):
    print(f"  {m}")
print("Rate limits raised. Watchfiles will auto-reload.")
