"""Restore production rate limits after SAT run."""
import re
TARGET = '/app/app/api/routes/health_v2.py'
with open(TARGET, 'r') as f:
    c = f.read()
c = re.sub(r'"strict":\s*\(500,\s*60\)',         '"strict": (10, 60)',  c)
c = re.sub(r'"unauthenticated":\s*\(500,\s*60\)', '"unauthenticated": (20, 60)', c)
c = re.sub(r'"authenticated":\s*\(500,\s*60\)',   '"authenticated": (60, 60)',  c)
with open(TARGET, 'w') as f:
    f.write(c)
# Verify
for m in re.findall(r'"(?:strict|unauthenticated|authenticated)":\s*\(\d+,\s*60\)', c):
    print(f"  {m}")
print("Production rate limits restored.")
