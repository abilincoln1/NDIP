"""
Read-only code inspection for D5A conformance audit.
Run: docker exec ndip-backend-1 python3 /tmp/audit_code.py
"""
import os, sys

def show_file(path, max_lines=60):
    try:
        lines = open(path).readlines()
        print(f"\n--- {path} ({len(lines)} lines) ---")
        for i, l in enumerate(lines[:max_lines]):
            print(f"{i+1}: {l}", end='')
        if len(lines) > max_lines:
            print(f"... [{len(lines)-max_lines} more lines]")
    except Exception as e:
        print(f"\n--- {path} --- ERROR: {e}")

def show_dir(path, depth=0):
    try:
        entries = sorted(os.listdir(path))
        for e in entries:
            full = os.path.join(path, e)
            prefix = "  " * depth
            if os.path.isdir(full) and e not in ['__pycache__','.git','node_modules']:
                print(f"{prefix}[DIR] {e}/")
                if depth < 2:
                    show_dir(full, depth+1)
            else:
                size = os.path.getsize(full) if os.path.isfile(full) else 0
                print(f"{prefix}{e} ({size}b)")
    except Exception as e:
        print(f"  ERROR listing {path}: {e}")

print("=" * 70)
print("NDIP BACKEND CODE STRUCTURE")
print("=" * 70)

show_dir('/app/app')

print("\n" + "=" * 70)
print("MAIN.PY — ROUTE REGISTRATIONS")
print("=" * 70)
show_file('/app/app/main.py', 120)

print("\n" + "=" * 70)
print("AUTH V3 ROUTES")
print("=" * 70)
show_file('/app/app/api/routes/auth_v3.py', 80)

print("\n" + "=" * 70)
print("TENANTS V3 ROUTES")
print("=" * 70)
show_file('/app/app/api/routes/tenants_v3.py', 60)

print("\n" + "=" * 70)
print("V2 ROUTES LISTING")
print("=" * 70)
try:
    routes = [f for f in os.listdir('/app/app/api/routes') if f.endswith('.py')]
    for r in sorted(routes):
        size = os.path.getsize(f'/app/app/api/routes/{r}')
        print(f"  {r} ({size}b)")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 70)
print("FRONTEND STRUCTURE")
print("=" * 70)
try:
    show_dir('/app/frontend/src', 0)
except:
    try:
        show_dir('/app/src', 0)
    except Exception as e:
        print(f"Frontend path not found: {e}")

print("\n" + "=" * 70)
print("DOCKER COMPOSE CONFIG")
print("=" * 70)
for path in ['/app/docker-compose.yml', '/app/docker-compose.yaml']:
    if os.path.exists(path):
        show_file(path, 80)
        break

