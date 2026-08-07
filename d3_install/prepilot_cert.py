"""
NDIP Phase D5 — Pre-Pilot Security Certification
=================================================
Run INSIDE the ndip-backend-1 container (has app settings + DB access):

    docker cp prepilot_cert.py ndip-backend-1:/tmp/prepilot_cert.py
    docker exec ndip-backend-1 python3 /tmp/prepilot_cert.py

Checks production-readiness of security-relevant configuration before the
Founder Pilot goes live. Never prints secret values — only pass/fail and
metadata (length, whether it matches a known-bad default, etc).

Exit code 0 = all checks passed. Exit code 1 = at least one FAIL.
WARN items do not fail the run but must be acknowledged in the cert report.
"""
import json
import os
import sys
from datetime import datetime, timezone

# The script is copied to /tmp inside the container, so /app (where the
# `app` package lives per docker-compose's ./backend:/app mount) is not on
# sys.path by default. Add it explicitly before any `from app...` import.
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

RESULTS = []


def check(name, passed, detail, severity="FAIL"):
    """severity is the label used when passed is False: FAIL or WARN"""
    status = "PASS" if passed else severity
    RESULTS.append({"check": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}")
    return passed


def main():
    print("=" * 70)
    print("NDIP Phase D5 — Pre-Pilot Security Certification")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    try:
        from app.core.config import get_settings
        settings = get_settings()
    except Exception as e:
        print(f"FATAL: could not import app settings: {e}")
        sys.exit(2)

    all_hard_pass = True

    # ── 1. SECRET_KEY ────────────────────────────────────────────────────
    default_key = "change-me-in-production-must-be-32-chars-min"
    key = settings.secret_key or ""
    key_ok = check(
        "SECRET_KEY strength",
        len(key) >= 32 and key != default_key,
        f"length={len(key)} chars, is_default={key == default_key}",
    )
    all_hard_pass &= key_ok

    # ── 2. APP_ENV ───────────────────────────────────────────────────────
    env_ok = check(
        "APP_ENV is production",
        settings.app_env.lower() == "production",
        f"app_env={settings.app_env!r} (expected 'production' before external pilot traffic)",
        severity="WARN",
    )

    # ── 3. JWT algorithm ─────────────────────────────────────────────────
    algo_ok = check(
        "JWT algorithm is HS256",
        settings.algorithm == "HS256",
        f"algorithm={settings.algorithm!r}",
    )
    all_hard_pass &= algo_ok

    # ── 4. Access token expiry sane for pilot ───────────────────────────
    expiry_ok = check(
        "Access token expiry <= 24h",
        0 < settings.access_token_expire_minutes <= 1440,
        f"access_token_expire_minutes={settings.access_token_expire_minutes}",
        severity="WARN",
    )

    # ── 5. CORS origins ──────────────────────────────────────────────────
    origins = settings.cors_origins_list
    cors_localhost_only = all("localhost" in o or "127.0.0.1" in o for o in origins)
    check(
        "CORS restricted to localhost (dev pilot)",
        cors_localhost_only,
        f"cors_origins={origins}. OK for internal/Stage-1-2 pilot; MUST be updated to production domain before public/national rollout.",
        severity="WARN",
    )

    # ── 6. Rate limiting config (imported from health_v2) ───────────────
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, "/app/app/api/routes")
        from health_v2 import RATE_LIMITS  # type: ignore
        expected = {"strict": (10, 60), "unauthenticated": (20, 60), "authenticated": (60, 60)}
        rl_ok = check(
            "Rate limits match production values",
            RATE_LIMITS == expected,
            f"RATE_LIMITS={RATE_LIMITS}",
        )
        all_hard_pass &= rl_ok
    except Exception as e:
        check("Rate limits match production values", False, f"could not import health_v2.RATE_LIMITS: {e}", severity="WARN")

    # ── 7. Bcrypt cost factor ───────────────────────────────────────────
    try:
        import bcrypt
        test_hash = bcrypt.hashpw(b"probe", bcrypt.gensalt(rounds=12)).decode()
        cost = int(test_hash.split("$")[2])
        cost_ok = check(
            "Bcrypt cost factor >= 12",
            cost >= 12,
            f"gensalt(rounds=12) produced cost={cost}",
        )
        all_hard_pass &= cost_ok
    except Exception as e:
        check("Bcrypt cost factor >= 12", False, f"could not verify: {e}", severity="WARN")

    # ── 8. Database connectivity + RBAC tables present ─────────────────
    try:
        from app.db.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_ok = check("Database reachable", True, "SELECT 1 succeeded")

            tbl_count = db.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"
            )).scalar()
            check("Database has expected table count", tbl_count >= 55,
                  f"table_count={tbl_count} (baseline: 60)", severity="WARN")

            # RBAC: every active member should have a role
            null_roles = db.execute(text(
                "SELECT COUNT(*) FROM members WHERE is_active AND role IS NULL"
            )).scalar()
            rbac_ok = check(
                "No active members missing an RBAC role",
                null_roles == 0,
                f"active members with NULL role={null_roles}",
            )
            all_hard_pass &= rbac_ok

            # Placeholder emails among INVITED cohort members
            placeholder = db.execute(text(
                "SELECT COUNT(*) FROM members WHERE email LIKE '%@invited.ndip.rtifn.org'"
            )).scalar()
            check(
                "Cohort placeholder emails remaining",
                placeholder == 0,
                f"{placeholder} member(s) still have placeholder invited.ndip.rtifn.org emails — must be resolved before those members can be invited/authenticate",
                severity="WARN",
            )
        finally:
            db.close()
    except Exception as e:
        check("Database reachable", False, f"error: {e}")
        all_hard_pass = False

    # ── 9. Redis connectivity ───────────────────────────────────────────
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        pong = r.ping()
        redis_ok = check("Redis reachable", bool(pong), f"PING -> {pong}")
        all_hard_pass &= redis_ok
    except Exception as e:
        check("Redis reachable", False, f"error: {e}")
        all_hard_pass = False

    # ── 10. SMTP / email delivery ───────────────────────────────────────
    smtp_configured = bool(os.getenv("SMTP_HOST"))
    check(
        "SMTP configured for real delivery",
        smtp_configured,
        "SMTP_HOST not set — DevNullEmailProvider active, invitation emails will NOT be delivered. Must configure before Stage 2/3 invitations go out."
        if not smtp_configured else "SMTP_HOST set — real delivery active",
        severity="WARN",
    )

    # ── 11. Secret-bearing env vars present (existence only, no values) ─
    secret_vars = [
        "SECRET_KEY", "ANTHROPIC_API_KEY", "YOUTUBE_API_KEY",
        "TWITTER_BEARER_TOKEN", "REDDIT_CLIENT_SECRET", "NEWS_API_KEY",
        "META_ACCESS_TOKEN",
    ]
    missing = [v for v in secret_vars if not os.getenv(v)]
    check(
        "All expected secret env vars present",
        len(missing) == 0,
        f"missing={missing}" if missing else "all present",
        severity="WARN",
    )

    # ── Summary ──────────────────────────────────────────────────────────
    print("=" * 70)
    fails = [r for r in RESULTS if r["status"] == "FAIL"]
    warns = [r for r in RESULTS if r["status"] == "WARN"]
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "overall": "CERTIFIED" if not fails else "NOT CERTIFIED",
        "fail_count": len(fails),
        "warn_count": len(warns),
        "results": RESULTS,
    }
    print(json.dumps(summary, indent=2))

    out_path = "/tmp/prepilot_cert_result.json"
    try:
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResult written to {out_path} inside container.")
        print(f"Copy out with: docker cp ndip-backend-1:{out_path} ./prepilot_cert_result.json")
    except Exception as e:
        print(f"Could not write result file: {e}")

    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
