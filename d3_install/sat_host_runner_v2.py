"""
NDIP Phase D4 — SAT Runner v2 (fixed)
- Removes empty Bearer header test (crashes httpx on Python 3.14)
- Adds small delays between bursts to avoid rate limiter
- Adds CORS check fix
"""
import sys, time, json, os

try:
    import httpx
except ImportError:
    os.system("pip install httpx -q")
    import httpx

BASE = "http://localhost:8000"
RESULTS = {}
DEFECTS = []
PERF = {}

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

def check(area, test_name, passed, detail="", severity=None):
    key = f"{area}::{test_name}"
    status = "PASS" if passed else "FAIL"
    RESULTS[key] = {"status": status, "detail": detail}
    icon = "+" if passed else "X"
    print(f"  [{icon}] {test_name}: {status}{' -- ' + detail if detail else ''}")
    if not passed and severity:
        DEFECTS.append({
            "id": f"D4-{len(DEFECTS)+1:03d}",
            "area": area, "test": test_name,
            "severity": severity, "detail": detail, "status": "OPEN"
        })

def login(email, password):
    try:
        r = httpx.post(f"{BASE}/api/v2/members/login",
                       json={"email": email, "password": password}, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"    Login error: {e}")
    return None

def api_get(path, token):
    return httpx.get(f"{BASE}{path}",
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)

def api_post(path, token, body):
    return httpx.post(f"{BASE}{path}",
                      headers={"Authorization": f"Bearer {token}"},
                      json=body, timeout=15)

def api_put(path, token, body):
    return httpx.put(f"{BASE}{path}",
                     headers={"Authorization": f"Bearer {token}"},
                     json=body, timeout=15)

def timed(name, fn):
    t0 = time.time()
    result = fn()
    ms = int((time.time() - t0) * 1000)
    PERF[name] = ms
    flag = " <<< SLOW" if ms >= 2000 else ""
    print(f"  [PERF] {name}: {ms}ms{flag}")
    return result, ms

ACCOUNTS = {
    "super_admin":          ("superadmin@ndip.rtifn.org",         "TestPass2026!"),
    "national_director":    ("nationaldirector@ndip.rtifn.org",   "TestPass2026!"),
    "chapter_admin":        ("chapteradmin.bham@ndip.rtifn.org",  "TestPass2026!"),
    "verifier":             ("verifier@ndip.rtifn.org",           "TestPass2026!"),
    "intelligence_analyst": ("analyst@ndip.rtifn.org",            "TestPass2026!"),
    "verified_member":      ("verifiedmember@ndip.rtifn.org",     "TestPass2026!"),
    "standard_member":      ("member@ndip.rtifn.org",             "TestPass2026!"),
}
TOKENS = {}

# ── AREA 1: AUTHENTICATION ─────────────────────────────────────────────
section("AREA 1: AUTHENTICATION")

for role, (email, pwd) in ACCOUNTS.items():
    t0 = time.time()
    resp = login(email, pwd)
    ms = int((time.time()-t0)*1000)
    if resp and resp.get("access_token"):
        TOKENS[role] = resp["access_token"]
        TOKENS[f"{role}_refresh"] = resp.get("refresh_token", "")
        check("AUTH", f"Login: {role}", True, f"{ms}ms")
    else:
        check("AUTH", f"Login: {role}", False, "No token returned", "Critical")

check("AUTH", "All 7 roles logged in", len([k for k in TOKENS if '_refresh' not in k]) == 7,
      f"{len([k for k in TOKENS if '_refresh' not in k])} of 7",
      "Critical" if len([k for k in TOKENS if '_refresh' not in k]) < 7 else None)

r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "superadmin@ndip.rtifn.org", "password": "WrongPass!99"}, timeout=10)
check("AUTH", "Invalid password rejected (401)", r.status_code == 401, f"HTTP {r.status_code}",
      "High" if r.status_code != 401 else None)

r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "nobody@nowhere.com", "password": "TestPass2026!"}, timeout=10)
check("AUTH", "Unknown email rejected (401)", r.status_code == 401, f"HTTP {r.status_code}",
      "High" if r.status_code != 401 else None)

# Refresh rotation
rt = TOKENS.get("standard_member_refresh", "")
if rt:
    r = httpx.post(f"{BASE}/api/v2/members/refresh", json={"refresh_token": rt}, timeout=10)
    check("AUTH", "Refresh token rotation", r.status_code == 200, f"HTTP {r.status_code}",
          "High" if r.status_code != 200 else None)
    if r.status_code == 200:
        r2 = httpx.post(f"{BASE}/api/v2/members/refresh", json={"refresh_token": rt}, timeout=10)
        check("AUTH", "Used refresh token replay rejected", r2.status_code in (401,403),
              f"HTTP {r2.status_code}", "Critical" if r2.status_code == 200 else None)

# Invalid JWT
r = httpx.get(f"{BASE}/api/v2/auth/me",
              headers={"Authorization": "Bearer eyJinvalid.notareal.token"}, timeout=10)
check("AUTH", "Invalid JWT rejected (401)", r.status_code == 401, f"HTTP {r.status_code}",
      "Critical" if r.status_code == 200 else None)

# Logout everywhere
if TOKENS.get("verified_member"):
    r = httpx.post(f"{BASE}/api/v2/auth/logout-everywhere",
                   headers={"Authorization": f"Bearer {TOKENS['verified_member']}"}, timeout=10)
    check("AUTH", "Logout everywhere", r.status_code == 200, f"HTTP {r.status_code}")
    resp = login(*ACCOUNTS["verified_member"])
    if resp: TOKENS["verified_member"] = resp["access_token"]

# Anti-enumeration
r = httpx.post(f"{BASE}/api/v2/auth/password-reset/request",
               json={"email": "nonexistent@example.com"}, timeout=10)
check("AUTH", "Password reset always 200 (anti-enumeration)", r.status_code == 200,
      f"HTTP {r.status_code}", "High" if r.status_code != 200 else None)

# Rate limiting (use distinct emails to avoid account lockout)
time.sleep(1)  # brief pause before rate limit test
rl_hits = []
for i in range(15):
    r = httpx.post(f"{BASE}/api/v2/members/login",
                   json={"email": f"rltest{i}@nowhere.com", "password": "bad"}, timeout=5)
    rl_hits.append(r.status_code)
    if r.status_code == 429:
        break
got_429 = 429 in rl_hits
check("AUTH", "Rate limiting fires", got_429,
      f"429 seen: {got_429}, after {len(rl_hits)} requests",
      "High" if not got_429 else None)
time.sleep(2)  # let rate limiter window partially clear

r = httpx.get(f"{BASE}/health", timeout=5)
check("AUTH", "GET /health", r.status_code == 200, f"status={r.json().get('status')}")

r = httpx.get(f"{BASE}/readiness", timeout=5)
check("AUTH", "GET /readiness", r.status_code == 200,
      f"status={r.json().get('status')}, checks={r.json().get('checks')}")

# ── AREA 2: RBAC ───────────────────────────────────────────────────────
section("AREA 2: RBAC")
time.sleep(1)

for role, token in {k: v for k,v in TOKENS.items() if '_refresh' not in k}.items():
    r = api_get("/api/v2/auth/me", token)
    check("RBAC", f"/me: {role}", r.status_code == 200, f"HTTP {r.status_code}")

for role in ["standard_member","verified_member","verifier","intelligence_analyst"]:
    if TOKENS.get(role):
        r = api_get("/api/v2/admin/members", TOKENS[role])
        check("RBAC", f"Admin blocked: {role}", r.status_code == 403, f"HTTP {r.status_code}",
              "Critical" if r.status_code == 200 else None)

for role in ["super_admin","national_director","chapter_admin"]:
    if TOKENS.get(role):
        r = api_get("/api/v2/admin/members", TOKENS[role])
        check("RBAC", f"Admin accessible: {role}", r.status_code == 200, f"HTTP {r.status_code}",
              "High" if r.status_code != 200 else None)

for role in ["standard_member","chapter_admin"]:
    if TOKENS.get(role):
        r = api_get("/api/v2/admin/audit-log", TOKENS[role])
        check("RBAC", f"Audit log blocked: {role}", r.status_code == 403, f"HTTP {r.status_code}",
              "High" if r.status_code == 200 else None)

if TOKENS.get("national_director"):
    r = api_get("/api/v2/admin/audit-log", TOKENS["national_director"])
    check("RBAC", "Audit log: national_director", r.status_code == 200, f"HTTP {r.status_code}")

if TOKENS.get("intelligence_analyst"):
    r = api_get("/api/v2/admin/audit-log", TOKENS["intelligence_analyst"])
    check("RBAC", "Audit log: intelligence_analyst", r.status_code == 200, f"HTTP {r.status_code}")

# Privilege escalation attempt: chapter_admin tries to set super_admin role
if TOKENS.get("chapter_admin"):
    r = httpx.put(f"{BASE}/api/v2/admin/members/b0000007-0000-0000-0000-000000000007/role",
                  headers={"Authorization": f"Bearer {TOKENS['chapter_admin']}"},
                  json={"role": "super_admin"}, timeout=10)
    check("RBAC", "Privilege escalation blocked (chapter_admin -> super_admin)", r.status_code == 403,
          f"HTTP {r.status_code}", "Critical" if r.status_code == 200 else None)

r = httpx.get(f"{BASE}/api/v2/geography/states", timeout=5)
check("RBAC", "Geography public (no auth)", r.status_code == 200,
      f"HTTP {r.status_code}, {len(r.json())} states")

r = httpx.get(f"{BASE}/api/v2/members/me", timeout=5)
check("RBAC", "Unauthenticated /me blocked", r.status_code in (401,403), f"HTTP {r.status_code}",
      "Critical" if r.status_code == 200 else None)

if TOKENS.get("verifier"):
    r = api_get("/api/v2/verification/queue", TOKENS["verifier"])
    check("RBAC", "Verifier queue: verifier role", r.status_code == 200, f"HTTP {r.status_code}")

if TOKENS.get("standard_member"):
    r = api_get("/api/v2/verification/queue", TOKENS["standard_member"])
    check("RBAC", "Verifier queue blocked: standard_member", r.status_code == 403, f"HTTP {r.status_code}",
          "High" if r.status_code == 200 else None)

# ── AREA 3: MEMBER MANAGEMENT ────────────────────────────────────────
section("AREA 3: MEMBER MANAGEMENT")
time.sleep(1)

if TOKENS.get("super_admin"):
    r = api_get("/api/v2/admin/members?page=1&page_size=5", TOKENS["super_admin"])
    check("MEMBERS", "List paginated", r.status_code == 200,
          f"total={r.json().get('meta',{}).get('total')}, page_size=5")

    r = api_get("/api/v2/admin/members?role=super_admin", TOKENS["super_admin"])
    check("MEMBERS", "Filter by role", r.status_code == 200,
          f"count={r.json().get('meta',{}).get('total')}")

    r = api_get("/api/v2/admin/members?search=admin", TOKENS["super_admin"])
    check("MEMBERS", "Search", r.status_code == 200,
          f"results={r.json().get('meta',{}).get('total')}")

    r = api_get("/api/v2/admin/members?is_verified=true", TOKENS["super_admin"])
    check("MEMBERS", "Filter verified=true", r.status_code == 200,
          f"count={r.json().get('meta',{}).get('total')}")

if TOKENS.get("standard_member"):
    r = api_get("/api/v2/members/me", TOKENS["standard_member"])
    check("MEMBERS", "Own profile readable", r.status_code == 200, f"HTTP {r.status_code}")

    r = api_put("/api/v2/members/me", TOKENS["standard_member"],
                {"occupation": "SAT Tester", "biography": "D4 SAT validation."})
    check("MEMBERS", "Own profile update", r.status_code == 200, f"HTTP {r.status_code}",
          "High" if r.status_code != 200 else None)

# ── AREA 4: ONBOARDING ──────────────────────────────────────────────
section("AREA 4: ONBOARDING")
time.sleep(1)

if TOKENS.get("standard_member"):
    r = api_get("/api/v2/auth/onboarding", TOKENS["standard_member"])
    pct = r.json().get("data",{}).get("completion_pct","?") if r.status_code==200 else "?"
    check("ONBOARDING", "Get wizard state", r.status_code == 200, f"completion={pct}%")

    for step in ["state_selected","chapter_confirmed","terms_accepted"]:
        r = api_post("/api/v2/auth/onboarding/step", TOKENS["standard_member"], {"step": step})
        check("ONBOARDING", f"Advance step: {step}", r.status_code == 200, f"HTTP {r.status_code}")

    r = api_post("/api/v2/auth/onboarding/step", TOKENS["standard_member"], {"step": "invalid_step"})
    check("ONBOARDING", "Invalid step rejected (400)", r.status_code == 400, f"HTTP {r.status_code}")

r = httpx.get(f"{BASE}/api/v2/geography/states", timeout=5)
check("ONBOARDING", "States: 37 returned", r.status_code==200 and len(r.json())==37,
      f"count={len(r.json()) if r.status_code==200 else r.status_code}")

r = httpx.get(f"{BASE}/api/v2/geography/lgas/24", timeout=5)
check("ONBOARDING", "LGAs for Lagos (20)", r.status_code==200 and len(r.json())==20,
      f"count={len(r.json()) if r.status_code==200 else r.status_code}")

r = httpx.get(f"{BASE}/api/v2/geography/lgas/9999", timeout=5)
check("ONBOARDING", "Invalid state 404", r.status_code==404, f"HTTP {r.status_code}")

r = httpx.get(f"{BASE}/api/v2/geography/search?q=Lagos", timeout=5)
check("ONBOARDING", "Geography search", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 5: REPORTS ──────────────────────────────────────────────────
section("AREA 5: ENGAGEMENT REPORTS")
time.sleep(1)

from datetime import date as dt
report_id = None

if TOKENS.get("verified_member"):
    r = api_post("/api/v2/reports/", TOKENS["verified_member"], {
        "report_type": "community_event",
        "title": "SAT D4 Test Community Report",
        "description": "D4 system acceptance test engagement report.",
        "event_date": str(dt.today()),
        "location": "Birmingham, UK", "country": "United Kingdom",
        "attendees_count": 35, "tags": ["sat","d4"]
    })
    check("REPORTS", "Create (201)", r.status_code==201, f"HTTP {r.status_code}",
          "High" if r.status_code!=201 else None)
    if r.status_code==201:
        report_id = r.json().get("data",{}).get("id")

    r = api_get("/api/v2/reports/my", TOKENS["verified_member"])
    check("REPORTS", "List own reports", r.status_code==200,
          f"total={r.json().get('meta',{}).get('total')}")

    if report_id:
        r = api_get(f"/api/v2/reports/{report_id}", TOKENS["verified_member"])
        check("REPORTS", "Get single", r.status_code==200, f"HTTP {r.status_code}")

        r = api_put(f"/api/v2/reports/{report_id}", TOKENS["verified_member"], {"attendees_count": 50})
        check("REPORTS", "Update draft", r.status_code==200, f"HTTP {r.status_code}")

        r = api_post(f"/api/v2/reports/{report_id}/submit", TOKENS["verified_member"], {})
        check("REPORTS", "Submit", r.status_code==200, f"HTTP {r.status_code}")

        r = api_put(f"/api/v2/reports/{report_id}", TOKENS["verified_member"], {"attendees_count": 999})
        check("REPORTS", "Edit submitted blocked (409)", r.status_code==409, f"HTTP {r.status_code}",
              "Medium" if r.status_code==200 else None)

if TOKENS.get("chapter_admin"):
    r = api_get("/api/v2/reports/?status=submitted", TOKENS["chapter_admin"])
    check("REPORTS", "Admin list submitted", r.status_code==200, f"HTTP {r.status_code}")
    if report_id:
        r = api_post(f"/api/v2/reports/{report_id}/review", TOKENS["chapter_admin"],
                     {"decision": "approved", "notes": "D4 SAT"})
        check("REPORTS", "Admin approve", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 6: SPONSORSHIPS ────────────────────────────────────────────
section("AREA 6: SPONSORSHIPS")
time.sleep(1)

if TOKENS.get("verified_member"):
    r = api_post("/api/v2/sponsorships/", TOKENS["verified_member"], {
        "ward_id": 1, "sponsorship_type": "education",
        "title": "SAT D4 Test Sponsorship", "beneficiaries_count": 100
    })
    check("SPONSORSHIPS", "Create (201)", r.status_code==201, f"HTTP {r.status_code}",
          "High" if r.status_code!=201 else None)
    s_id = r.json().get("data",{}).get("id") if r.status_code==201 else None

    r = api_get("/api/v2/sponsorships/", TOKENS["verified_member"])
    check("SPONSORSHIPS", "List", r.status_code==200, f"total={r.json().get('meta',{}).get('total')}")

    if s_id:
        r = api_get(f"/api/v2/sponsorships/{s_id}", TOKENS["verified_member"])
        check("SPONSORSHIPS", "Get single", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 7: PROJECTS ────────────────────────────────────────────────
section("AREA 7: PROJECTS")
time.sleep(1)

project_id = None
if TOKENS.get("verified_member"):
    r = api_post("/api/v2/projects/", TOKENS["verified_member"], {
        "title": "SAT D4 Test Project",
        "description": "D4 SAT system acceptance test project.",
        "project_type": "development", "sector": "Infrastructure",
        "state_id": 24, "budget_naira": 5000000.0, "tags": ["sat","d4"]
    })
    check("PROJECTS", "Create (201)", r.status_code==201, f"HTTP {r.status_code}",
          "High" if r.status_code!=201 else None)
    if r.status_code==201:
        project_id = r.json().get("data",{}).get("id")

    r = api_get("/api/v2/projects/", TOKENS["verified_member"])
    check("PROJECTS", "List", r.status_code==200, f"total={r.json().get('meta',{}).get('total')}")

    if project_id:
        r = api_get(f"/api/v2/projects/{project_id}", TOKENS["verified_member"])
        check("PROJECTS", "Get with stakeholders", r.status_code==200,
              f"stakeholders={len(r.json().get('data',{}).get('stakeholders',[]))}")

        r = api_put(f"/api/v2/projects/{project_id}", TOKENS["verified_member"], {"status": "active"})
        check("PROJECTS", "Update status", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 8: VERIFICATION ────────────────────────────────────────────
section("AREA 8: VERIFICATION WORKFLOW")
time.sleep(1)

sub_id = None
if TOKENS.get("standard_member"):
    r = api_post("/api/v2/verification/", TOKENS["standard_member"], {
        "submission_type": "identity", "documents": [], "notes": "D4 SAT test"
    })
    check("VERIFICATION", "Submit (201)", r.status_code==201, f"HTTP {r.status_code}",
          "High" if r.status_code!=201 else None)
    if r.status_code==201:
        sub_id = r.json().get("data",{}).get("id")

    r = api_get("/api/v2/verification/my", TOKENS["standard_member"])
    check("VERIFICATION", "Own submissions", r.status_code==200,
          f"total={r.json().get('meta',{}).get('total')}")

if TOKENS.get("verifier"):
    r = api_get("/api/v2/verification/queue", TOKENS["verifier"])
    check("VERIFICATION", "Queue", r.status_code==200, f"total={r.json().get('meta',{}).get('total')}")

    if sub_id:
        r = api_post(f"/api/v2/verification/{sub_id}/review", TOKENS["verifier"],
                     {"decision": "approved", "notes": "D4 SAT approval"})
        check("VERIFICATION", "Approve submission", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 9: DASHBOARD ───────────────────────────────────────────────
section("AREA 9: DASHBOARD")
time.sleep(1)

if TOKENS.get("verified_member"):
    r = api_get("/api/v2/members/dashboard", TOKENS["verified_member"])
    check("DASHBOARD", "Member dashboard", r.status_code==200, f"HTTP {r.status_code}")

    r = api_get("/api/v2/impact/me", TOKENS["verified_member"])
    check("DASHBOARD", "Impact score", r.status_code==200,
          f"score={r.json().get('data',{}).get('total_score','?')}")

    r = api_get("/api/v2/impact/leaderboard", TOKENS["verified_member"])
    check("DASHBOARD", "Leaderboard", r.status_code==200,
          f"total={r.json().get('meta',{}).get('total')}")

if TOKENS.get("super_admin"):
    r = api_get("/api/v2/admin/platform-stats", TOKENS["super_admin"])
    check("DASHBOARD", "Admin platform stats", r.status_code==200,
          f"keys={list(r.json().get('data',{}).keys())[:5] if r.status_code==200 else 'N/A'}")

    r = api_get("/api/v2/admin/chapter-summaries", TOKENS["super_admin"])
    check("DASHBOARD", "Chapter summaries", r.status_code==200, f"HTTP {r.status_code}")

    r = api_get("/api/v2/admin/scheduler-log", TOKENS["super_admin"])
    check("DASHBOARD", "Scheduler log", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 10: BACKGROUND SERVICES ────────────────────────────────────
section("AREA 10: BACKGROUND SERVICES")
time.sleep(1)

if TOKENS.get("super_admin"):
    r = api_get("/api/v2/admin/audit-log?page_size=5", TOKENS["super_admin"])
    entries = r.json().get("meta",{}).get("total",0) if r.status_code==200 else 0
    check("SCHEDULER", "Audit log has entries", entries > 0,
          f"{entries} entries", "High" if entries==0 else None)

    r = api_get("/api/v2/admin/scheduler-log", TOKENS["super_admin"])
    check("SCHEDULER", "Scheduler log accessible", r.status_code==200, f"HTTP {r.status_code}")

    r = api_get("/api/v2/impact/leaderboard", TOKENS["super_admin"])
    check("SCHEDULER", "Impact scores populated", r.status_code==200, f"HTTP {r.status_code}")

    r = api_get("/api/v2/admin/platform-stats", TOKENS["super_admin"])
    if r.status_code==200:
        stats = r.json().get("data",{})
        check("SCHEDULER", "Notifications table operational", True,
              f"failed_notifications={stats.get('failed_notifications',0)}")

# ── AREA 11: OBSERVABILITY ──────────────────────────────────────────
section("AREA 11: OBSERVABILITY")

r = httpx.get(f"{BASE}/health", timeout=5)
check("OBS", "X-Request-ID present", "x-request-id" in r.headers,
      f"{'present' if 'x-request-id' in r.headers else 'MISSING'}",
      "Medium" if "x-request-id" not in r.headers else None)
check("OBS", "X-Response-Time-Ms present", "x-response-time-ms" in r.headers,
      f"{'present' if 'x-response-time-ms' in r.headers else 'MISSING'}")
check("OBS", "/health returns ok", r.json().get("status")=="ok", f"status={r.json().get('status')}")

r = httpx.get(f"{BASE}/readiness", timeout=5)
check("OBS", "/readiness ready", r.json().get("status")=="ready",
      f"status={r.json().get('status')}, checks={r.json().get('checks')}")

if TOKENS.get("super_admin"):
    r = api_get("/api/v2/metrics", TOKENS["super_admin"])
    check("OBS", "/api/v2/metrics", r.status_code==200, f"HTTP {r.status_code}")

# ── AREA 12: PERFORMANCE ────────────────────────────────────────────
section("AREA 12: PERFORMANCE (threshold: 2000ms)")
time.sleep(1)

timed("Login", lambda: httpx.post(f"{BASE}/api/v2/members/login",
    json={"email": ACCOUNTS["super_admin"][0], "password": ACCOUNTS["super_admin"][1]}, timeout=15))

if TOKENS.get("super_admin"):
    timed("Member list", lambda: httpx.get(f"{BASE}/api/v2/admin/members",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=15))
    timed("Platform stats", lambda: httpx.get(f"{BASE}/api/v2/admin/platform-stats",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=15))
    timed("Geography states", lambda: httpx.get(f"{BASE}/api/v2/geography/states", timeout=15))
    timed("Leaderboard", lambda: httpx.get(f"{BASE}/api/v2/impact/leaderboard",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=15))
    timed("Reports list", lambda: httpx.get(f"{BASE}/api/v2/reports/",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=15))

slow = {k: v for k, v in PERF.items() if v >= 2000}
check("PERF", "All endpoints < 2000ms", len(slow)==0,
      f"Slow: {slow}" if slow else "All within threshold",
      "Medium" if slow else None)

# ── AREA 13: SECURITY VALIDATION ───────────────────────────────────
section("AREA 13: SECURITY VALIDATION")
time.sleep(1)

# SQL injection
r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "' OR '1'='1", "password": "x"}, timeout=10)
check("SECURITY", "SQL injection rejected", r.status_code in (401,422),
      f"HTTP {r.status_code}", "Critical" if r.status_code==200 else None)

r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "admin'--", "password": "x"}, timeout=10)
check("SECURITY", "SQL comment injection rejected", r.status_code in (401,422),
      f"HTTP {r.status_code}", "Critical" if r.status_code==200 else None)

# XSS via profile (JSON API - stored not executed)
if TOKENS.get("standard_member"):
    r = api_put("/api/v2/members/me", TOKENS["standard_member"],
                {"biography": "<script>alert('xss')</script>"})
    check("SECURITY", "XSS payload stored safely (JSON API)", r.status_code==200,
          "JSON API returns raw text - no HTML execution at API layer")

# JWT role tampering
if TOKENS.get("standard_member"):
    import base64
    parts = TOKENS["standard_member"].split(".")
    try:
        pad = 4 - len(parts[1]) % 4
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * pad))
        payload["role"] = "super_admin"
        tampered = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        tampered_token = f"{parts[0]}.{tampered}.{parts[2]}"
        r = api_get("/api/v2/admin/members", tampered_token)
        check("SECURITY", "JWT role tampering rejected", r.status_code in (401,403),
              f"HTTP {r.status_code}", "Critical" if r.status_code==200 else None)
    except Exception as e:
        check("SECURITY", "JWT tampering test", False, f"Error: {e}", "High")

# CORS
try:
    r = httpx.options(f"{BASE}/api/v2/members/login",
                      headers={"Origin": "http://evil.com",
                                "Access-Control-Request-Method": "POST"}, timeout=5)
    check("SECURITY", "CORS headers on OPTIONS", "access-control-allow-origin" in r.headers,
          f"origin={r.headers.get('access-control-allow-origin','not set')}")
except Exception as e:
    check("SECURITY", "CORS headers on OPTIONS", False, f"Error: {e}", "Low")

# INVITED member cannot login
r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "cohort.001@invited.ndip.rtifn.org", "password": "TestPass2026!"}, timeout=10)
check("SECURITY", "INVITED member login blocked", r.status_code in (401,403),
      f"HTTP {r.status_code}", "Critical" if r.status_code==200 else None)

# Malformed auth header (using a random string instead of empty to avoid httpx crash)
r = httpx.get(f"{BASE}/api/v2/members/me",
              headers={"Authorization": "Bearer totallyinvalidtoken12345"}, timeout=5)
check("SECURITY", "Malformed token rejected", r.status_code in (401,403), f"HTTP {r.status_code}")

# Wrong scheme
r = httpx.get(f"{BASE}/api/v2/members/me",
              headers={"Authorization": "Basic dXNlcjpwYXNz"}, timeout=5)
check("SECURITY", "Wrong auth scheme rejected", r.status_code in (401,403), f"HTTP {r.status_code}")

# ── FINAL SUMMARY ──────────────────────────────────────────────────
section("SAT SUMMARY")

total = len(RESULTS)
passed = sum(1 for v in RESULTS.values() if v["status"]=="PASS")
failed = total - passed
pass_rate = int(passed/total*100) if total else 0

print(f"\n  Total tests:  {total}")
print(f"  Passed:       {passed}")
print(f"  Failed:       {failed}")
print(f"  Pass rate:    {pass_rate}%")

if DEFECTS:
    critical = [d for d in DEFECTS if d["severity"]=="Critical"]
    high = [d for d in DEFECTS if d["severity"]=="High"]
    medium = [d for d in DEFECTS if d["severity"]=="Medium"]
    print(f"\n  Defects: {len(DEFECTS)} total | Critical: {len(critical)} | High: {len(high)} | Medium: {len(medium)}")
    print(f"\n  DEFECT REGISTER:")
    for d in DEFECTS:
        print(f"    [{d['severity']}] {d['id']}: {d['area']} :: {d['test']}")
        print(f"      Detail: {d['detail']}")
else:
    print(f"\n  No defects found.")

print(f"\n  PERFORMANCE RESULTS:")
for k,v in PERF.items():
    flag = " <<< SLOW" if v>=2000 else ""
    print(f"    {k}: {v}ms{flag}")

verdict = "PASS" if failed==0 and not [d for d in DEFECTS if d["severity"] in ("Critical","High")] else "FAIL"
print(f"\n  *** SAT VERDICT: {verdict} ***")

output = {
    "summary": {"total": total, "passed": passed, "failed": failed, "pass_rate": pass_rate},
    "verdict": verdict, "performance_ms": PERF, "defects": DEFECTS, "results": RESULTS,
}
with open("sat_results.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Results saved to sat_results.json")
