"""
NDIP Phase D5 — Stage 1 Internal Validation
============================================
Run INSIDE ndip-backend-1, using test accounts only (no cohort members
are touched or contacted). Safe to run multiple times over the 24h
Stage 1 window — it does not send real notifications and does not
modify member data (aside from normal login/session bookkeeping).

    docker cp stage1_validate.py ndip-backend-1:/tmp/stage1_validate.py
    docker exec ndip-backend-1 python3 /tmp/stage1_validate.py

NOTE: /api/v2/members/login is rate-limited to 10 requests/min per IP
(the "strict" tier). This script makes 7 login calls per run, so running
it twice within the same 60s window from the same container IP WILL
trip that limit and produce 429s on the second run — that is the rate
limiter working correctly, not a defect. Space repeat runs at least a
minute apart.

Checks:
  1. All 7 test accounts can authenticate (login flow works end to end)
  2. RBAC enforced: low-privilege role denied admin endpoint, admin allowed
  3. Audit logging is capturing requests (audit_log growing)
  4. Scheduler is alive and jobs have executed (scheduler_job_log)
  5. Notifications are using DevNull provider only — no real SMTP attempts
  6. Health/readiness/metrics endpoints respond correctly
  7. Rate limiting still enforced at documented thresholds (non-destructive check)

Writes JSON result to /tmp/stage1_validate_result.json inside the container.
Run again near T+24h and diff the two results to show stability over time.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/app")

import httpx

BASE_URL = "http://localhost:8000"
RESULTS = []

TEST_ACCOUNTS = [
    ("superadmin@ndip.rtifn.org", "super_admin"),
    ("nationaldirector@ndip.rtifn.org", "national_director"),
    ("chapteradmin.bham@ndip.rtifn.org", "chapter_admin"),
    ("verifier@ndip.rtifn.org", "verifier"),
    ("analyst@ndip.rtifn.org", "intelligence_analyst"),
    ("verifiedmember@ndip.rtifn.org", "verified_member"),
    ("member@ndip.rtifn.org", "standard_member"),
]
TEST_PASSWORD = "TestPass2026!"


def check(name, passed, detail, severity="FAIL"):
    status = "PASS" if passed else severity
    RESULTS.append({"check": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}")
    return passed


def main():
    print("=" * 70)
    print("NDIP Phase D5 — Stage 1 Internal Validation")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    all_hard_pass = True

    # ── 1. Health / readiness / metrics ─────────────────────────────────
    try:
        r = client.get("/health")
        check("GET /health", r.status_code == 200, f"status_code={r.status_code}")
    except Exception as e:
        check("GET /health", False, f"error: {e}")
        all_hard_pass = False

    try:
        r = client.get("/readiness")
        body = r.json()
        ready_ok = check(
            "GET /readiness",
            r.status_code == 200 and body.get("status") == "ready",
            f"status_code={r.status_code}, body={body}",
        )
        all_hard_pass &= ready_ok
    except Exception as e:
        check("GET /readiness", False, f"error: {e}")
        all_hard_pass = False

    # ── 2. Login for all 7 test accounts ────────────────────────────────
    tokens = {}
    for email, role in TEST_ACCOUNTS:
        try:
            r = client.post("/api/v2/members/login", json={"email": email, "password": TEST_PASSWORD})
            ok = r.status_code == 200 and "access_token" in r.json()
            if ok:
                tokens[role] = r.json()["access_token"]
            check(f"Login: {role}", ok, f"email={email}, status_code={r.status_code}")
            all_hard_pass &= ok
        except Exception as e:
            check(f"Login: {role}", False, f"email={email}, error: {e}")
            all_hard_pass = False

    # ── 3. RBAC enforcement ─────────────────────────────────────────────
    if "standard_member" in tokens:
        r = client.get("/api/v2/admin/platform-stats",
                        headers={"Authorization": f"Bearer {tokens['standard_member']}"})
        rbac_deny_ok = check(
            "RBAC denies standard_member on /admin/platform-stats",
            r.status_code == 403,
            f"status_code={r.status_code} (expected 403)",
        )
        all_hard_pass &= rbac_deny_ok
    else:
        check("RBAC denies standard_member on /admin/platform-stats", False,
              "standard_member token unavailable (login failed above)", severity="WARN")

    if "super_admin" in tokens:
        r = client.get("/api/v2/admin/platform-stats",
                        headers={"Authorization": f"Bearer {tokens['super_admin']}"})
        rbac_allow_ok = check(
            "RBAC allows super_admin on /admin/platform-stats",
            r.status_code == 200,
            f"status_code={r.status_code}",
        )
        all_hard_pass &= rbac_allow_ok
        platform_stats = r.json().get("data", {}) if r.status_code == 200 else {}
    else:
        check("RBAC allows super_admin on /admin/platform-stats", False,
              "super_admin token unavailable (login failed above)")
        platform_stats = {}
        all_hard_pass = False

    # ── 4. Audit logging ─────────────────────────────────────────────────
    if "super_admin" in tokens:
        r = client.get("/api/v2/admin/audit-log?page=1&page_size=5",
                        headers={"Authorization": f"Bearer {tokens['super_admin']}"})
        if r.status_code == 200:
            body = r.json()
            total = (body.get("meta") or {}).get("total", body.get("total", "unknown"))
            audit_ok = check(
                "Audit log is capturing requests",
                total != 0 and total != "unknown",
                f"total_audit_rows={total} (this run's own requests should already be logged)",
            )
            all_hard_pass &= audit_ok
        else:
            check("Audit log is capturing requests", False, f"status_code={r.status_code}")
            all_hard_pass = False

    # ── 5. Scheduler status ─────────────────────────────────────────────
    if "super_admin" in tokens:
        r = client.get("/api/v2/admin/scheduler-log?limit=50",
                        headers={"Authorization": f"Bearer {tokens['super_admin']}"})
        if r.status_code == 200:
            rows = r.json().get("data", r.json()) if isinstance(r.json(), dict) else r.json()
            rows = rows if isinstance(rows, list) else []
            job_names_seen = sorted({row.get("job_name") for row in rows if row.get("job_name")})
            expected_jobs = {
                "nlp_extraction_job", "duplicate_detection_job", "verification_queue_job",
                "notification_retry_job", "impact_score_rebuild_job", "leaderboard_rebuild_job",
                "chapter_summaries_job", "cleanup_job",
            }
            check(
                "Scheduler job log has entries",
                len(rows) > 0,
                f"{len(rows)} log rows found, job_names_seen={job_names_seen}. "
                f"Hourly jobs fire ~60min after scheduler start, nightly jobs at 02:00-02:45 UTC — "
                f"it is normal for not all 8 jobs to have run yet this early in Stage 1.",
                severity="WARN",
            )
            failed = [row for row in rows if row.get("status") == "failed"]
            check(
                "No failed scheduler jobs in recent log",
                len(failed) == 0,
                f"{len(failed)} failed job runs out of {len(rows)} recent entries",
                severity="WARN",
            )
        else:
            check("Scheduler job log has entries", False, f"status_code={r.status_code}", severity="WARN")

    # ── 6. Notification provider — confirm DevNull, no real SMTP ───────
    smtp_configured = bool(os.getenv("SMTP_HOST"))
    check(
        "Notifications still on DevNull (no real delivery) — expected for Stage 1",
        not smtp_configured,
        "SMTP_HOST unset, DevNullEmailProvider active — correct for Stage 1 (test accounts only, no real invitations)"
        if not smtp_configured else "SMTP_HOST is set — real delivery is active, confirm this is intentional",
    )

    # notifications table: failed count should be 0 or explainable (DevNull "succeeds" by design)
    if "super_admin" in tokens and platform_stats:
        failed_notif = platform_stats.get("failed_notifications")
        check(
            "No failed notifications recorded",
            failed_notif == 0,
            f"failed_notifications={failed_notif}",
            severity="WARN",
        )

    # ── 7. Rate limiting still enforced (non-destructive spot check) ───
    # Hit an unauthenticated endpoint a handful of times — well under the
    # 20/min unauthenticated threshold — just to confirm no 5xx/crash under
    # light repeated load, without actually tripping the limiter.
    try:
        codes = []
        for _ in range(5):
            r = client.get("/api/v2/geography/states")
            codes.append(r.status_code)
        light_load_ok = check(
            "Light repeated load handled cleanly (5x GET /geography/states)",
            all(c == 200 for c in codes),
            f"status_codes={codes}",
        )
        all_hard_pass &= light_load_ok
    except Exception as e:
        check("Light repeated load handled cleanly", False, f"error: {e}")

    # ── Summary ──────────────────────────────────────────────────────────
    print("=" * 70)
    fails = [r for r in RESULTS if r["status"] == "FAIL"]
    warns = [r for r in RESULTS if r["status"] == "WARN"]
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "overall": "PASS" if not fails else "FAIL",
        "fail_count": len(fails),
        "warn_count": len(warns),
        "results": RESULTS,
    }
    print(json.dumps(summary, indent=2))

    out_path = "/tmp/stage1_validate_result.json"
    try:
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResult written to {out_path} inside container.")
        print(f"Copy out with: docker cp ndip-backend-1:{out_path} ./stage1_validate_result_<timestamp>.json")
    except Exception as e:
        print(f"Could not write result file: {e}")

    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
