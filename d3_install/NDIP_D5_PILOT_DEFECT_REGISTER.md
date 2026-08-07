# NDIP Phase D5 — Pilot Defect Register
**Prepared by:** Chief Engineering AI (Claude, Cowork)
**Date:** 03 August 2026
**Approved scope:** Founder Pilot defect tracking (Deliverable 7 of 10)

---

## DEFECT-001: AuditLogMiddleware silently failing on every insert

| Field | Value |
|---|---|
| **Found during** | Stage 1 Internal Validation, T+0 baseline run |
| **Severity** | High |
| **Status** | FIXED — 03 August 2026 |
| **Component** | `backend/app/api/middleware/audit.py` — `AuditLogMiddleware` |

### Description
The audit log is supposed to record every API request (user, endpoint, method, IP, response code, duration) per `audit_log` table, registered as global middleware since Phase D3. In practice, `audit_log` contained exactly 1 row total as of 03 August 2026 — a single `/sat/test` entry from 02 August — despite the platform having served the full D4 SAT run (99 tests) and normal operation since.

### Root Cause
The INSERT statement cast the IP address inline as `:ip_address::inet`. SQLAlchemy's `text()` bind-parameter parser does not reliably bind a named parameter immediately followed by a Postgres `::` cast operator — this is the same class of issue already called out in this project's canonical environment constraints for JSONB columns ("JSONB insertion: `PgJson()` or `CAST(:param AS jsonb)`" — never `:param::jsonb`). Because `:ip_address` was never substituted, Postgres received the literal token `:ip_address::inet`, which is invalid syntax, and every insert raised a `ProgrammingError`. The middleware wrapped this in a bare `except Exception: pass`, so the failure was invisible — no log line, no error response, nothing — for every single request since the middleware went live.

### Impact
No usable audit trail exists for any period before 03 August 2026 15:49 UTC (fix deployed). This includes the entire Phase D4 System Acceptance Testing run and all activity between D4 completion and D5 Stage 1 kickoff. The `/api/v2/admin/audit-log` endpoint (RBAC-gated to national_director/super_admin) was returning correctly-shaped empty results, so this would not have been visually obvious without automated validation actively checking row counts before/after known request volume.

### Fix
Changed the INSERT to `CAST(:ip_address AS inet)`. Verified live: row count went from 1 to 2 immediately after the fix, with `ip_address`, `endpoint`, `method`, `response_code`, and `created_at` all populated correctly on the new row.

Additionally hardened the failure-handling: the bare `except: pass` was replaced with `logger.error(...)` logging the full traceback, so any future audit-write failure will surface in `docker logs ndip-backend-1` instead of failing silently again.

### Verification
```
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "SELECT COUNT(*) FROM audit_log;"
```
Confirmed incrementing correctly after the fix (1 → 2, then continuing to grow with the Stage 1 T+0 re-run).

### Follow-up
- No historical audit trail can be recovered for Aug 2 – Aug 3 (fix time). This gap should be noted in any compliance reporting that references audit coverage for the D4 SAT period.
- Recommend a lightweight automated check (e.g. periodic row-count assertion) be added to CI or the scheduler so a regression like this is caught within hours, not weeks.

---

*No other defects identified during Stage 1 T+0 validation. This register will be updated if further issues surface during the 24h Stage 1 window.*
