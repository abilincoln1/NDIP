#!/usr/bin/env python3
"""SF-3: Health check with retry — resolves startup timing failures.
Usage: python3 /app/app/health_check_retry.py [host] [attempts] [delay_secs]
"""
import sys, time, urllib.request

host = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 5
delay = int(sys.argv[3]) if len(sys.argv) > 3 else 3

for i in range(1, attempts + 1):
    try:
        r = urllib.request.urlopen(f'{host}/health', timeout=5)
        if r.status == 200:
            print(f'Backend healthy (attempt {i}/{attempts})')
            sys.exit(0)
    except Exception as e:
        print(f'Health check {i}/{attempts} failed: {e}')
        if i < attempts:
            time.sleep(delay)

print(f'Backend not healthy after {attempts} attempts')
sys.exit(1)
