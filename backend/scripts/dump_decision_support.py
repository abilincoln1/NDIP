"""Dump line-numbered content of decision_support.py around the suspect area for inspection."""
path = '/app/app/services/decision_support.py'
lines = open(path).readlines()
print(f"Total lines: {len(lines)}")
print("--- Lines 380-420 ---")
for i, line in enumerate(lines[379:420], start=380):
    print(f"{i}: {line.rstrip()}")
