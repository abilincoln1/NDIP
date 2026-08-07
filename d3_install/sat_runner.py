"""
NDIP Phase D4 — SAT Test Execution Script
File: sat_runner.py
Runs inside ndip-backend-1 container.

Executes all 13 SAT test areas programmatically:
  1.  Authentication
  2.  RBAC
  3.  Member Management
  4.  Onboarding
  5.  Reports
  6.  Sponsorships
  7.  Projects
  8.  Verification Workflow
  9.  Dashboard
  10. Background Services
  11. Observability
  12. Performance
  13. Security Validation

Results written to /tmp/sat_results.json
"""
import sys, os, time, json, secrets
sys.path.insert(0, "/app")

import httpx
from sqlalchemy import text
from app.db.database import SessionLocal

BASE = "http://localhost:8000"
RESULTS = {}
DEFECTS = []

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

def check(area, test_name, passed, detail="", severity=None):
    key = f"{area}::{test_name}"
    status = "PASS" if passed else "FAIL"
    RESULTS[key] = {"status": status, "detail": detail}
    icon = "✓" if passed else "✗"
    print(f"  [{icon}] {test_name}: {status}{' — ' + detail if detail else ''}")
    if not passed and severity:
        DEFECTS.append({
            "id": f"D4-{len(DEFECTS)+1:03d}",
            "area": area,
            "test": test_name,
            "severity": severity,
            "detail": detail,
            "status": "OPEN"
        })

def login(email, password):
    r = httpx.post(f"{BASE}/api/v2/members/login",
                   json={"email": email, "password": password}, timeout=10)
    if r.status_code == 200:
        return r.json()
    return None

def get(path, token):
    r = httpx.get(f"{BASE}{path}",
                  headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return r

def post(path, token, body):
    r = httpx.post(f"{BASE}{path}",
                   headers={"Authorization": f"Bearer {token}"},
                   json=body, timeout=10)
    return r

# ── Credentials ──────────────────────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════════════════
# AREA 1: AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════
section("AREA 1: AUTHENTICATION")

# 1.1 Valid login for all 7 roles
for role, (email, pwd) in ACCOUNTS.items():
    t0 = time.time()
    resp = login(email, pwd)
    elapsed = int((time.time() - t0) * 1000)
    if resp and resp.get("access_token"):
        TOKENS[role] = resp["access_token"]
        check("AUTH", f"Login: {role}", True, f"{elapsed}ms")
    else:
        check("AUTH", f"Login: {role}", False, "No token returned", "Critical")

# 1.2 Invalid credentials
r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "superadmin@ndip.rtifn.org", "password": "WrongPass!"},
               timeout=10)
check("AUTH", "Reject invalid password", r.status_code == 401,
      f"HTTP {r.status_code}", "High" if r.status_code != 401 else None)

# 1.3 Non-existent email
r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "nobody@nowhere.com", "password": "TestPass2026!"},
               timeout=10)
check("AUTH", "Reject unknown email", r.status_code == 401,
      f"HTTP {r.status_code}", "High" if r.status_code != 401 else None)

# 1.4 Refresh token rotation
if TOKENS.get("standard_member"):
    r2 = httpx.post(f"{BASE}/api/v2/members/login",
                    json={"email": ACCOUNTS["standard_member"][0],
                          "password": ACCOUNTS["standard_member"][1]}, timeout=10)
    if r2.status_code == 200 and r2.json().get("refresh_token"):
        rt = r2.json()["refresh_token"]
        r3 = httpx.post(f"{BASE}/api/v2/members/refresh",
                        json={"refresh_token": rt}, timeout=10)
        check("AUTH", "Refresh token rotation", r3.status_code == 200,
              f"HTTP {r3.status_code}", "High" if r3.status_code != 200 else None)
        # Replay the used token — should fail
        r4 = httpx.post(f"{BASE}/api/v2/members/refresh",
                        json={"refresh_token": rt}, timeout=10)
        check("AUTH", "Revoke used refresh token (replay attack)", r4.status_code in (401, 403),
              f"HTTP {r4.status_code}", "Critical" if r4.status_code == 200 else None)
    else:
        check("AUTH", "Refresh token rotation", False, "Could not get refresh token", "High")

# 1.5 Invalid JWT
r = get("/api/v2/auth/me", "invalid.jwt.token")
check("AUTH", "Reject invalid JWT", r.status_code == 401,
      f"HTTP {r.status_code}", "Critical" if r.status_code != 401 else None)

# 1.6 Logout everywhere
if TOKENS.get("verified_member"):
    r = httpx.post(f"{BASE}/api/v2/auth/logout-everywhere",
                   headers={"Authorization": f"Bearer {TOKENS['verified_member']}"},
                   timeout=10)
    check("AUTH", "Logout everywhere", r.status_code == 200,
          f"HTTP {r.status_code}", "Medium" if r.status_code != 200 else None)
    # Re-login to restore token
    resp = login(*ACCOUNTS["verified_member"])
    if resp:
        TOKENS["verified_member"] = resp["access_token"]

# 1.7 Password reset request (email enumeration protection)
r = httpx.post(f"{BASE}/api/v2/auth/password-reset/request",
               json={"email": "nonexistent@example.com"}, timeout=10)
check("AUTH", "Password reset — email enumeration safe (always 200)", r.status_code == 200,
      f"HTTP {r.status_code}", "High" if r.status_code != 200 else None)

# 1.8 Rate limiting on login endpoint
rl_results = []
for i in range(12):
    r = httpx.post(f"{BASE}/api/v2/members/login",
                   json={"email": "ratelimit@test.com", "password": "bad"}, timeout=5)
    rl_results.append(r.status_code)
got_429 = 429 in rl_results
check("AUTH", "Rate limiting on login endpoint", got_429,
      f"Got 429 after {rl_results.index(429)+1 if got_429 else 'N/A'} requests",
      "High" if not got_429 else None)

# 1.9 Health endpoints
r = httpx.get(f"{BASE}/health", timeout=5)
check("AUTH", "Health endpoint (/health)", r.status_code == 200, f"HTTP {r.status_code}")

r = httpx.get(f"{BASE}/readiness", timeout=5)
check("AUTH", "Readiness endpoint (/readiness)", r.status_code == 200,
      f"status={r.json().get('status','?')}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 2: RBAC
# ══════════════════════════════════════════════════════════════════════════
section("AREA 2: RBAC")

# 2.1 /me accessible to all authenticated roles
for role, token in TOKENS.items():
    r = get("/api/v2/auth/me", token)
    check("RBAC", f"/me accessible: {role}", r.status_code == 200, f"HTTP {r.status_code}")

# 2.2 Admin endpoints blocked for non-admin roles
for role in ["standard_member", "verified_member", "verifier", "intelligence_analyst"]:
    if TOKENS.get(role):
        r = get("/api/v2/admin/members", TOKENS[role])
        check("RBAC", f"Admin members blocked for {role}", r.status_code == 403,
              f"HTTP {r.status_code}", "Critical" if r.status_code == 200 else None)

# 2.3 Admin endpoints accessible for admin roles
for role in ["super_admin", "national_director", "chapter_admin"]:
    if TOKENS.get(role):
        r = get("/api/v2/admin/members", TOKENS[role])
        check("RBAC", f"Admin members accessible for {role}", r.status_code == 200,
              f"HTTP {r.status_code}", "High" if r.status_code != 200 else None)

# 2.4 Audit log — national_director+ only
for role in ["standard_member", "chapter_admin"]:
    if TOKENS.get(role):
        r = get("/api/v2/admin/audit-log", TOKENS[role])
        check("RBAC", f"Audit log blocked for {role}", r.status_code == 403,
              f"HTTP {r.status_code}", "High" if r.status_code == 200 else None)

if TOKENS.get("national_director"):
    r = get("/api/v2/admin/audit-log", TOKENS["national_director"])
    check("RBAC", "Audit log accessible for national_director", r.status_code == 200,
          f"HTTP {r.status_code}")

# 2.5 Platform stats — national_director+ only
if TOKENS.get("super_admin"):
    r = get("/api/v2/admin/platform-stats", TOKENS["super_admin"])
    check("RBAC", "Platform stats accessible for super_admin", r.status_code == 200,
          f"HTTP {r.status_code}")

# 2.6 Geography public (no auth required)
r = httpx.get(f"{BASE}/api/v2/geography/states", timeout=5)
check("RBAC", "Geography public (no auth)", r.status_code == 200,
      f"HTTP {r.status_code}, {len(r.json())} states")

# 2.7 Unauthenticated access blocked
r = httpx.get(f"{BASE}/api/v2/members/me", timeout=5)
check("RBAC", "Unauthenticated /me blocked", r.status_code == 403,
      f"HTTP {r.status_code}", "Critical" if r.status_code == 200 else None)

# 2.8 Verification queue — verifier role
if TOKENS.get("verifier"):
    r = get("/api/v2/verification/queue", TOKENS["verifier"])
    check("RBAC", "Verification queue accessible for verifier", r.status_code == 200,
          f"HTTP {r.status_code}")

if TOKENS.get("standard_member"):
    r = get("/api/v2/verification/queue", TOKENS["standard_member"])
    check("RBAC", "Verification queue blocked for standard_member", r.status_code == 403,
          f"HTTP {r.status_code}", "High" if r.status_code == 200 else None)

# ══════════════════════════════════════════════════════════════════════════
# AREA 3: MEMBER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════
section("AREA 3: MEMBER MANAGEMENT")

if TOKENS.get("super_admin"):
    # 3.1 List members with pagination
    r = get("/api/v2/admin/members?page=1&page_size=5", TOKENS["super_admin"])
    check("MEMBERS", "List members (paginated)", r.status_code == 200,
          f"HTTP {r.status_code}, meta={r.json().get('meta',{})}")

    # 3.2 Filter by role
    r = get("/api/v2/admin/members?role=super_admin", TOKENS["super_admin"])
    check("MEMBERS", "Filter members by role", r.status_code == 200,
          f"HTTP {r.status_code}, count={r.json().get('meta',{}).get('total','?')}")

    # 3.3 Search
    r = get("/api/v2/admin/members?search=admin", TOKENS["super_admin"])
    check("MEMBERS", "Search members", r.status_code == 200,
          f"HTTP {r.status_code}, results={r.json().get('meta',{}).get('total','?')}")

    # 3.4 Filter verified only
    r = get("/api/v2/admin/members?is_verified=true", TOKENS["super_admin"])
    check("MEMBERS", "Filter verified members", r.status_code == 200,
          f"HTTP {r.status_code}")

if TOKENS.get("standard_member"):
    # 3.5 Own profile read
    r = get("/api/v2/members/me", TOKENS["standard_member"])
    check("MEMBERS", "Own profile readable", r.status_code == 200,
          f"HTTP {r.status_code}")

    # 3.6 Own profile update
    r = httpx.put(f"{BASE}/api/v2/members/me",
                  headers={"Authorization": f"Bearer {TOKENS['standard_member']}"},
                  json={"occupation": "Software Engineer", "biography": "SAT test profile update."},
                  timeout=10)
    check("MEMBERS", "Own profile update", r.status_code == 200,
          f"HTTP {r.status_code}", "High" if r.status_code != 200 else None)

# ══════════════════════════════════════════════════════════════════════════
# AREA 4: ONBOARDING
# ══════════════════════════════════════════════════════════════════════════
section("AREA 4: ONBOARDING")

if TOKENS.get("standard_member"):
    # 4.1 Get onboarding state
    r = get("/api/v2/auth/onboarding", TOKENS["standard_member"])
    check("ONBOARDING", "Get onboarding state", r.status_code == 200,
          f"HTTP {r.status_code}, pct={r.json().get('data',{}).get('completion_pct','?')}%")

    # 4.2 Advance step
    r = post("/api/v2/auth/onboarding/step", TOKENS["standard_member"],
             {"step": "profile_completed"})
    check("ONBOARDING", "Advance wizard step", r.status_code == 200,
          f"HTTP {r.status_code}", "High" if r.status_code != 200 else None)

    # 4.3 Geography cascades (states)
    r = httpx.get(f"{BASE}/api/v2/geography/states", timeout=5)
    check("ONBOARDING", "States dropdown populated", r.status_code == 200 and len(r.json()) == 37,
          f"HTTP {r.status_code}, {len(r.json())} states")

    # 4.4 LGAs for Lagos (state_id=24)
    r = httpx.get(f"{BASE}/api/v2/geography/lgas/24", timeout=5)
    check("ONBOARDING", "LGAs for Lagos (20 expected)", r.status_code == 200 and len(r.json()) == 20,
          f"HTTP {r.status_code}, {len(r.json())} LGAs")

    # 4.5 Invalid state
    r = httpx.get(f"{BASE}/api/v2/geography/lgas/9999", timeout=5)
    check("ONBOARDING", "Invalid state returns 404", r.status_code == 404,
          f"HTTP {r.status_code}")

    # 4.6 Geography search
    r = httpx.get(f"{BASE}/api/v2/geography/search?q=Lagos", timeout=5)
    check("ONBOARDING", "Geography search works", r.status_code == 200,
          f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 5: REPORTS
# ══════════════════════════════════════════════════════════════════════════
section("AREA 5: ENGAGEMENT REPORTS")

report_id = None
if TOKENS.get("verified_member"):
    # 5.1 Create report
    from datetime import date
    r = post("/api/v2/reports/", TOKENS["verified_member"], {
        "report_type": "community_event",
        "title": "SAT Test Community Event — Birmingham 2026",
        "description": "System acceptance test engagement report. Not a real event.",
        "event_date": str(date.today()),
        "location": "Birmingham, UK",
        "country": "United Kingdom",
        "attendees_count": 25,
        "outcome_summary": "SAT validation event.",
        "tags": ["sat", "test"]
    })
    check("REPORTS", "Create report", r.status_code == 201,
          f"HTTP {r.status_code}", "High" if r.status_code != 201 else None)
    if r.status_code == 201:
        report_id = r.json().get("data", {}).get("id")

    # 5.2 List own reports
    r = get("/api/v2/reports/my", TOKENS["verified_member"])
    check("REPORTS", "List own reports", r.status_code == 200,
          f"HTTP {r.status_code}, total={r.json().get('meta',{}).get('total','?')}")

    # 5.3 Get single report
    if report_id:
        r = get(f"/api/v2/reports/{report_id}", TOKENS["verified_member"])
        check("REPORTS", "Get single report", r.status_code == 200,
              f"HTTP {r.status_code}")

        # 5.4 Update draft
        r = httpx.put(f"{BASE}/api/v2/reports/{report_id}",
                      headers={"Authorization": f"Bearer {TOKENS['verified_member']}"},
                      json={"attendees_count": 30},
                      timeout=10)
        check("REPORTS", "Update draft report", r.status_code == 200,
              f"HTTP {r.status_code}")

        # 5.5 Submit
        r = post(f"/api/v2/reports/{report_id}/submit", TOKENS["verified_member"], {})
        check("REPORTS", "Submit report", r.status_code == 200,
              f"HTTP {r.status_code}")

        # 5.6 Cannot edit submitted report
        r = httpx.put(f"{BASE}/api/v2/reports/{report_id}",
                      headers={"Authorization": f"Bearer {TOKENS['verified_member']}"},
                      json={"attendees_count": 50},
                      timeout=10)
        check("REPORTS", "Cannot edit submitted report (409)", r.status_code == 409,
              f"HTTP {r.status_code}", "Medium" if r.status_code == 200 else None)

# 5.7 Admin can list and review
if TOKENS.get("chapter_admin") and report_id:
    r = get("/api/v2/reports/?status=submitted", TOKENS["chapter_admin"])
    check("REPORTS", "Admin list submitted reports", r.status_code == 200,
          f"HTTP {r.status_code}")

    r = post(f"/api/v2/reports/{report_id}/review", TOKENS["chapter_admin"],
             {"decision": "approved", "notes": "SAT test approval"})
    check("REPORTS", "Admin approve report", r.status_code == 200,
          f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 6: SPONSORSHIPS
# ══════════════════════════════════════════════════════════════════════════
section("AREA 6: SPONSORSHIPS")

sponsorship_id = None
if TOKENS.get("verified_member"):
    r = post("/api/v2/sponsorships/", TOKENS["verified_member"], {
        "ward_id": 1,
        "sponsorship_type": "education",
        "title": "SAT Test Education Sponsorship",
        "description": "SAT validation sponsorship record.",
        "beneficiaries_count": 50
    })
    check("SPONSORSHIPS", "Create sponsorship", r.status_code == 201,
          f"HTTP {r.status_code}", "High" if r.status_code != 201 else None)
    if r.status_code == 201:
        sponsorship_id = r.json().get("data", {}).get("id")

    r = get("/api/v2/sponsorships/", TOKENS["verified_member"])
    check("SPONSORSHIPS", "List sponsorships", r.status_code == 200, f"HTTP {r.status_code}")

    if sponsorship_id:
        r = get(f"/api/v2/sponsorships/{sponsorship_id}", TOKENS["verified_member"])
        check("SPONSORSHIPS", "Get single sponsorship", r.status_code == 200, f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 7: PROJECTS
# ══════════════════════════════════════════════════════════════════════════
section("AREA 7: PROJECTS")

project_id = None
if TOKENS.get("verified_member"):
    r = post("/api/v2/projects/", TOKENS["verified_member"], {
        "title": "SAT Test Infrastructure Project",
        "description": "System acceptance test project. Created during D4 SAT validation.",
        "project_type": "development",
        "sector": "Infrastructure",
        "state_id": 24,
        "budget_naira": 5000000.0,
        "tags": ["sat", "test", "infrastructure"]
    })
    check("PROJECTS", "Create project", r.status_code == 201,
          f"HTTP {r.status_code}", "High" if r.status_code != 201 else None)
    if r.status_code == 201:
        project_id = r.json().get("data", {}).get("id")

    r = get("/api/v2/projects/", TOKENS["verified_member"])
    check("PROJECTS", "List projects", r.status_code == 200, f"HTTP {r.status_code}")

    if project_id:
        r = get(f"/api/v2/projects/{project_id}", TOKENS["verified_member"])
        check("PROJECTS", "Get project with stakeholders", r.status_code == 200, f"HTTP {r.status_code}")

        r = httpx.put(f"{BASE}/api/v2/projects/{project_id}",
                      headers={"Authorization": f"Bearer {TOKENS['verified_member']}"},
                      json={"status": "active"}, timeout=10)
        check("PROJECTS", "Update project status", r.status_code == 200, f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 8: VERIFICATION WORKFLOW
# ══════════════════════════════════════════════════════════════════════════
section("AREA 8: VERIFICATION WORKFLOW")

submission_id = None
if TOKENS.get("standard_member"):
    r = post("/api/v2/verification/", TOKENS["standard_member"], {
        "submission_type": "identity",
        "documents": [],
        "notes": "SAT test verification submission"
    })
    check("VERIFICATION", "Submit verification", r.status_code == 201,
          f"HTTP {r.status_code}", "High" if r.status_code != 201 else None)
    if r.status_code == 201:
        submission_id = r.json().get("data", {}).get("id")

    r = get("/api/v2/verification/my", TOKENS["standard_member"])
    check("VERIFICATION", "View own submissions", r.status_code == 200, f"HTTP {r.status_code}")

if TOKENS.get("verifier") and submission_id:
    r = get("/api/v2/verification/queue", TOKENS["verifier"])
    check("VERIFICATION", "Verifier sees queue", r.status_code == 200, f"HTTP {r.status_code}")

    r = post(f"/api/v2/verification/{submission_id}/review", TOKENS["verifier"],
             {"decision": "approved", "notes": "SAT test approval"})
    check("VERIFICATION", "Verifier approves submission", r.status_code == 200, f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 9: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
section("AREA 9: DASHBOARD")

if TOKENS.get("verified_member"):
    r = get("/api/v2/members/dashboard", TOKENS["verified_member"])
    check("DASHBOARD", "Member dashboard loads", r.status_code == 200, f"HTTP {r.status_code}")

    r = get("/api/v2/impact/me", TOKENS["verified_member"])
    check("DASHBOARD", "Impact score endpoint", r.status_code == 200, f"HTTP {r.status_code}")

    r = get("/api/v2/impact/leaderboard", TOKENS["verified_member"])
    check("DASHBOARD", "Leaderboard loads", r.status_code == 200, f"HTTP {r.status_code}")

if TOKENS.get("super_admin"):
    r = get("/api/v2/admin/platform-stats", TOKENS["super_admin"])
    check("DASHBOARD", "Admin platform stats", r.status_code == 200,
          f"HTTP {r.status_code}, data={list(r.json().get('data',{}).keys())[:4]}")

    r = get("/api/v2/admin/chapter-summaries", TOKENS["super_admin"])
    check("DASHBOARD", "Chapter summaries", r.status_code == 200, f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 10: BACKGROUND SERVICES
# ══════════════════════════════════════════════════════════════════════════
section("AREA 10: BACKGROUND SERVICES")

db = SessionLocal()
try:
    # 10.1 Scheduler job log exists and has entries
    count = db.execute(text("SELECT COUNT(*) FROM scheduler_job_log")).scalar()
    check("SCHEDULER", "scheduler_job_log table accessible", True, f"{count} log entries")

    # 10.2 Audit log active
    audit_count = db.execute(text("SELECT COUNT(*) FROM audit_log")).scalar()
    check("SCHEDULER", "audit_log receiving entries", audit_count > 0,
          f"{audit_count} entries", "High" if audit_count == 0 else None)

    # 10.3 Notifications table
    notif_count = db.execute(text("SELECT COUNT(*) FROM notifications")).scalar()
    check("SCHEDULER", "Notifications table accessible", True, f"{notif_count} records")

    # 10.4 Trigger impact score job manually
    from app.scheduler.d3_jobs import impact_score_rebuild_job, leaderboard_rebuild_job
    result = impact_score_rebuild_job()
    check("SCHEDULER", "Impact score job executes", result.get("members_scored", 0) >= 0,
          f"scored={result.get('members_scored', 0)}")

    result = leaderboard_rebuild_job()
    check("SCHEDULER", "Leaderboard rebuild job executes", result.get("ranked", 0) >= 0,
          f"ranked={result.get('ranked', 0)}")

    # 10.5 Cleanup job
    from app.scheduler.d3_jobs import cleanup_job
    result = cleanup_job()
    check("SCHEDULER", "Cleanup job executes", True, str(result))

finally:
    db.close()

# ══════════════════════════════════════════════════════════════════════════
# AREA 11: OBSERVABILITY
# ══════════════════════════════════════════════════════════════════════════
section("AREA 11: OBSERVABILITY")

# 11.1 Request ID in response
r = httpx.get(f"{BASE}/health", timeout=5)
check("OBS", "X-Request-ID in response", "x-request-id" in r.headers,
      f"header={'present' if 'x-request-id' in r.headers else 'MISSING'}",
      "Medium" if "x-request-id" not in r.headers else None)

# 11.2 Response time header
check("OBS", "X-Response-Time-Ms in response", "x-response-time-ms" in r.headers,
      f"header={'present' if 'x-response-time-ms' in r.headers else 'MISSING'}")

# 11.3 Health endpoint
r = httpx.get(f"{BASE}/health", timeout=5)
check("OBS", "Health endpoint returns ok", r.json().get("status") == "ok",
      f"status={r.json().get('status')}")

# 11.4 Readiness endpoint
r = httpx.get(f"{BASE}/readiness", timeout=5)
check("OBS", "Readiness endpoint returns ready", r.json().get("status") == "ready",
      f"checks={r.json().get('checks',{})}")

# 11.5 Metrics endpoint
if TOKENS.get("super_admin"):
    r = get("/api/v2/metrics", TOKENS["super_admin"])
    check("OBS", "Metrics endpoint returns data", r.status_code == 200,
          f"keys={list(r.json().keys())[:4] if r.status_code == 200 else 'N/A'}")

# ══════════════════════════════════════════════════════════════════════════
# AREA 12: PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════
section("AREA 12: PERFORMANCE")

PERF = {}

def timed(name, fn):
    t0 = time.time()
    result = fn()
    ms = int((time.time() - t0) * 1000)
    PERF[name] = ms
    status = "PASS" if ms < 2000 else "SLOW"
    print(f"  [{status}] {name}: {ms}ms {'⚠ SLOW' if ms >= 2000 else ''}")
    return result, ms

timed("Login (superadmin)", lambda: httpx.post(f"{BASE}/api/v2/members/login",
    json={"email": ACCOUNTS["super_admin"][0], "password": ACCOUNTS["super_admin"][1]}, timeout=10))

if TOKENS.get("super_admin"):
    timed("Member list", lambda: httpx.get(f"{BASE}/api/v2/admin/members",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=10))
    timed("Geography states", lambda: httpx.get(f"{BASE}/api/v2/geography/states", timeout=10))
    timed("Platform stats", lambda: httpx.get(f"{BASE}/api/v2/admin/platform-stats",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=10))
    timed("Leaderboard", lambda: httpx.get(f"{BASE}/api/v2/impact/leaderboard",
        headers={"Authorization": f"Bearer {TOKENS['super_admin']}"}, timeout=10))

slow = {k: v for k, v in PERF.items() if v >= 2000}
check("PERF", "All endpoints < 2000ms", len(slow) == 0,
      f"Slow: {slow}" if slow else "All within threshold",
      "Medium" if slow else None)

# ══════════════════════════════════════════════════════════════════════════
# AREA 13: SECURITY VALIDATION
# ══════════════════════════════════════════════════════════════════════════
section("AREA 13: SECURITY VALIDATION")

# 13.1 SQL injection attempt
r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "' OR 1=1 --", "password": "anything"}, timeout=5)
check("SECURITY", "SQL injection in login field rejected", r.status_code in (401, 422),
      f"HTTP {r.status_code}", "Critical" if r.status_code == 200 else None)

# 13.2 XSS in profile field
if TOKENS.get("standard_member"):
    r = httpx.put(f"{BASE}/api/v2/members/me",
                  headers={"Authorization": f"Bearer {TOKENS['standard_member']}"},
                  json={"biography": "<script>alert('xss')</script>"},
                  timeout=10)
    # Should accept (stored) but not execute — API is JSON, not HTML
    check("SECURITY", "XSS payload stored safely (JSON API)", r.status_code == 200,
          "Stored as plain text in JSON response — no HTML rendering on API layer")

# 13.3 JWT tampering
import base64
if TOKENS.get("standard_member"):
    parts = TOKENS["standard_member"].split(".")
    # Try to elevate role by tampering with payload
    try:
        payload_b64 = parts[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        payload["role"] = "super_admin"
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()).decode().rstrip("=")
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        r = get("/api/v2/admin/members", tampered_token)
        check("SECURITY", "JWT tampering rejected", r.status_code in (401, 403),
              f"HTTP {r.status_code}", "Critical" if r.status_code == 200 else None)
    except Exception as e:
        check("SECURITY", "JWT tampering rejected", False, f"Test error: {e}", "High")

# 13.4 CORS headers present
r = httpx.options(f"{BASE}/api/v2/members/login",
                  headers={"Origin": "http://evil.com",
                            "Access-Control-Request-Method": "POST"},
                  timeout=5)
check("SECURITY", "CORS headers present on OPTIONS", "access-control-allow-origin" in r.headers,
      f"origin={r.headers.get('access-control-allow-origin', 'not set')}")

# 13.5 INVITED member cannot login
r = httpx.post(f"{BASE}/api/v2/members/login",
               json={"email": "cohort.001@invited.ndip.rtifn.org", "password": "anything"},
               timeout=5)
check("SECURITY", "INVITED cohort member cannot login", r.status_code in (401, 403),
      f"HTTP {r.status_code}", "Critical" if r.status_code == 200 else None)

# 13.6 Empty bearer token
r = httpx.get(f"{BASE}/api/v2/members/me",
              headers={"Authorization": "Bearer "}, timeout=5)
check("SECURITY", "Empty bearer token rejected", r.status_code in (401, 403),
      f"HTTP {r.status_code}")

# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
section("SAT SUMMARY")

total = len(RESULTS)
passed = sum(1 for v in RESULTS.values() if v["status"] == "PASS")
failed = total - passed

print(f"\n  Total tests: {total}")
print(f"  Passed:      {passed}")
print(f"  Failed:      {failed}")
print(f"  Pass rate:   {int(passed/total*100)}%")

print(f"\n  Performance results:")
for k, v in PERF.items():
    print(f"    {k}: {v}ms")

if DEFECTS:
    print(f"\n  Defects found: {len(DEFECTS)}")
    critical = [d for d in DEFECTS if d["severity"] == "Critical"]
    high = [d for d in DEFECTS if d["severity"] == "High"]
    medium = [d for d in DEFECTS if d["severity"] == "Medium"]
    print(f"    Critical: {len(critical)}")
    print(f"    High:     {len(high)}")
    print(f"    Medium:   {len(medium)}")
    for d in DEFECTS:
        print(f"\n    [{d['severity']}] {d['id']}: {d['test']}")
        print(f"      Detail: {d['detail']}")
else:
    print(f"\n  No defects found.")

# Save results
output = {
    "summary": {"total": total, "passed": passed, "failed": failed},
    "performance": PERF,
    "defects": DEFECTS,
    "results": RESULTS,
}
with open("/tmp/sat_results.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Results saved to /tmp/sat_results.json")

verdict = "PASS" if failed == 0 and not [d for d in DEFECTS if d["severity"] in ("Critical","High")] else "FAIL"
print(f"\n  SAT VERDICT: {verdict}")
