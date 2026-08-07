# NDIP Phase D5 — Pre-Pilot Security Certification
**Prepared by:** Chief Engineering AI (Claude, Cowork)
**Date:** 03 August 2026
**Approved scope:** Founder Pilot pre-pilot security certification (Deliverable 1 of 10)
**Run at:** 2026-08-03T14:04:28Z (inside `ndip-backend-1`)
**Script:** `d3_install/prepilot_cert.py` — raw output: `d3_install/prepilot_cert_result.json`

---

## Overall Result

**CERTIFIED** — 0 FAIL, 9 PASS, 4 WARN.

No hard-fail (blocking) security issues found. Four WARN items are flagged below; none block Stage 1 Internal Validation, but three of the four must be resolved before Stage 2/3 (external cohort invitations) and one before national rollout.

---

## Correction to Prior Handover

The 02 August 2026 handover report stated `prepilot_cert.py` was "ready, not yet run" and implied it already existed in `d3_install`. On connecting to the live environment (03 August 2026), neither the script nor a D5 baseline SQL file were actually present on disk or in git history. `prepilot_cert.py` was rewritten from scratch against the current codebase (`app/core/config.py`, `app/core/security.py`, `d3_install/health_v2.py`, `d3_install/notification_service.py`) and executed successfully. This certification reflects that rewritten script's first run.

---

## Certification Checks

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | SECRET_KEY strength | ✅ PASS | 64 chars, not the known default value |
| 2 | APP_ENV is production | ⚠️ WARN | `app_env='development'` — expected `production` before external pilot traffic |
| 3 | JWT algorithm | ✅ PASS | HS256 |
| 4 | Access token expiry | ✅ PASS | 1440 min (24h) — within acceptable range |
| 5 | CORS origins | ✅ PASS | Restricted to `http://localhost:3000` — correct for this stage; must change before public/national rollout |
| 6 | Rate limits | ✅ PASS | Matches production values: strict 10/min, unauthenticated 20/min, authenticated 60/min |
| 7 | Bcrypt cost factor | ✅ PASS | Cost 12 |
| 8 | Database reachable | ✅ PASS | `SELECT 1` succeeded |
| 9 | Database table count | ✅ PASS | 60 tables (matches D2.5 baseline) |
| 10 | RBAC role coverage | ✅ PASS | 0 active members missing a role |
| 11 | Cohort placeholder emails | ⚠️ WARN | 3 members still on `@invited.ndip.rtifn.org` placeholder domain: Femi Olumiwaga, Aminu Ogbolu, and unused spare slot NDIP-2026-000110 |
| 12 | Redis reachable | ✅ PASS | PING → True |
| 13 | SMTP delivery configured | ⚠️ WARN | `SMTP_HOST` unset — `DevNullEmailProvider` active, no real email delivery |
| 14 | Secret env vars present | ⚠️ WARN | Missing (non-blocking, social-listening features only): `TWITTER_BEARER_TOKEN`, `REDDIT_CLIENT_SECRET`, `META_ACCESS_TOKEN` |

---

## WARN Items — Detail and Required Action

### 1. APP_ENV = development
The application is still configured with `app_env=development`. This does not currently gate any security behavior (rate limits, CORS, and secret handling are already production values regardless of `APP_ENV`), but the flag should be set to `production` before Stage 2 external invitations go out, since some future logging/error-detail behavior may key off it.

**Action:** Set `APP_ENV=production` in `backend/.env`, restart `ndip-backend-1`.

### 2. Cohort placeholder emails
Confirmed via live DB query: 3 of the 10 cohort slots still carry `@invited.ndip.rtifn.org` placeholder emails — Femi Olumiwaga (NDIP-2026-000103), Aminu Ogbolu (NDIP-2026-000104), and the unused spare slot (NDIP-2026-000110). This is unchanged from the handover except that **Osazemen Adun's placeholder has been resolved** (real email `osazadun@gmail.com` supplied by project owner 03 August 2026 and confirmed live in the DB via `d3_install/update_adun_email.py`).

This does not block Stage 1 (test accounts only) or Stage 2 (Shote, Adun, Olayiwola — all have real emails). It blocks Stage 3 (full cohort) for the two remaining real people; the spare slot (000110) is unused and can be left as-is or removed.

**Action:** Obtain real emails for Olumiwaga and Ogbolu before Stage 3.

### 3. SMTP not configured
`SMTP_HOST` is unset, so the platform uses `DevNullEmailProvider` — notification emails are logged to stdout, never delivered. This was already known and documented pre-pilot. It does not block Stage 1 (no real invitations sent). It **hard-blocks** Stage 2 and Stage 3, since invitation emails will not reach cohort members without it.

**Action:** Configure `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM` in `backend/.env` and verify with a live test send before Stage 2.

### 4. Missing optional secret env vars
`TWITTER_BEARER_TOKEN`, `REDDIT_CLIENT_SECRET`, and `META_ACCESS_TOKEN` are unset. These feed social-listening/data-ingestion features (Phase B), not the pilot's core member-facing flows. Non-blocking for D5.

**Action:** None required for D5; revisit if social listening features are needed for the pilot.

---

## Items Verified Safe (No Action Needed)

- SECRET_KEY is a properly rotated 64-character value, not the shipped default.
- Bcrypt cost factor (12) and JWT configuration (HS256, 24h expiry) meet standard practice.
- Rate limiting is live and matches the documented production values across all three tiers.
- RBAC is fully populated — no active member lacks a role.
- Database (60 tables) and Redis are both reachable and healthy.
- CORS is deliberately scoped to `localhost:3000` for this pilot stage — correct, not a defect, but flagged as a pre-national-rollout item (already tracked in known issues).

---

## Sign-off

| Item | Status |
|---|---|
| Certification run | COMPLETE |
| Result | CERTIFIED (0 FAIL / 9 PASS / 4 WARN) |
| Blocking issues for Stage 1 | None |
| Blocking issues for Stage 2 | SMTP delivery must be configured |
| Blocking issues for Stage 3 | SMTP delivery + 2 remaining real emails (Olumiwaga, Ogbolu) |

**Recommendation:** Proceed to Stage 1 Internal Validation. Configure SMTP before Stage 2.

*Report generated from `d3_install/prepilot_cert_result.json` — raw JSON retained as evidence.*
