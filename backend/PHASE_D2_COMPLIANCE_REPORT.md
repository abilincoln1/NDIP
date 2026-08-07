# Phase D.2 Compliance Report — Members Foundation

**To:** Chief Solutions Architect
**From:** Chief Engineering AI (Claude)
**Date:** 31 July 2026
**Subject:** Compliance verification — Phase D.2 Members Foundation implementation
**Status:** Implementation complete, sandbox-verified. **Not yet deployed
to `ndip-backend-1`/`ndip-db-1`** — deployment requires running the
migration and smoke tests against the live containers (steps in
`PHASE_D2_IMPLEMENTATION.md` §12), which needs to happen on your side of
the Docker environment as in Phase D.1. Per the directive's Stop
Condition, no work has begun on D.3 or any later module.

## 1. Executive Summary

Phase D.2 — Members Foundation is implemented in full: migration, four
ORM models plus one disclosed support model, repository layer, service
layer, JWT-based authentication reusing existing infrastructure, a
seven-role RBAC dependency, nine API endpoints, 36 tests, and both
required documentation files. Everything below was verified against a
real PostgreSQL 16.2 instance and a real FastAPI `TestClient` running the
actual shipped code — including a live 20-thread concurrency test of the
membership-number generator, and a deliberate reproduction of the exact
production bug found in Phase D.1 to confirm it cannot recur here. Three
deviations from the literal directive are disclosed in §9; none were
silently absorbed.

## 2. Migration Summary

`migrations/phase_d_02_members.sql`: transactional (single `BEGIN`/
`COMMIT`), idempotent, additive-only.

| Check | Result |
|---|---|
| No `ALTER` statements | PASS — confirmed by direct search of the file |
| No `DROP` statements | PASS — confirmed by direct search of the file |
| No modification of existing tables | PASS — only `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` / `INSERT ... ON CONFLICT` |
| Idempotent re-run | PASS — ran twice against the same database; second run produced zero new rows and only "already exists, skipping" notices |
| UUID generation | PASS — native `gen_random_uuid()`, confirmed available with no extension on PostgreSQL 16.2 |

Tables created: `chapters`, `members`, `member_profiles`,
`member_sessions`, `member_number_counters` (fifth table, disclosed —
see §9). Seed data: 4 reference chapters (Lagos, Abuja/FCT, Diaspora–US,
Diaspora–UK), 0 members.

## 3. Database Verification

Verified directly via `information_schema` queries and row counts against
a disposable PostgreSQL instance:

- All 5 tables created with correct columns, types, and nullability.
- All foreign keys present and enforced: `chapters.state_id → ng_states`,
  `members.state_of_origin_id/lga_of_origin_id → ng_states/ng_lgas`,
  `members.admin_user_id → admin_users` (`ON DELETE SET NULL`),
  `members.chapter_id → chapters`, `member_profiles.member_id → members`
  (`ON DELETE CASCADE`), `member_sessions.member_id → members`
  (`ON DELETE CASCADE`).
- All specified indexes present: `email`, `membership_number`,
  `chapter_id`, `state_of_origin_id`, `lga_of_origin_id`, `is_active`
  (members); `name`, `country`, `state_id`, `status` (chapters);
  `member_id`, `expires_at`, `revoked_at` (member_sessions).
- Partial unique indexes (`email`, `membership_number`, `name`) confirmed
  to allow reuse after soft delete and reject duplicates while a row is
  live — both directions tested
  (`test_soft_deleted_email_can_be_reused`,
  `test_registration_rejects_duplicate_email`).
- **Regression test for the Phase D.1 production bug**: called
  `Base.metadata.create_all()` against a disposable database *before*
  running the SQL migration (simulating `uvicorn --reload` hot-reload
  creating tables first, exactly what caused the Phase D.1 `created_at`
  NOT NULL failure). Result: the migration ran cleanly with zero errors,
  regardless of which one runs first, because `created_at`/`updated_at`/
  `id` now carry matching `server_default` values in both the ORM models
  and the raw SQL — this was fixed proactively, not after a failure.

## 4. API Verification

All 9 endpoints exercised via a live FastAPI `TestClient` against the
actual router/service/repository code (not a mock):

| Endpoint | Verified |
|---|---|
| `POST /register` | 201, returns tokens + member; rejects duplicate email (409), weak password (400), unknown chapter (404) |
| `POST /login` | 200 with valid credentials; 401 on wrong password; 403 on inactive account |
| `POST /refresh` | 200, rotates token; presenting the same refresh token twice returns 401 on the second attempt |
| `POST /logout` | 204; idempotent on invalid/already-used tokens |
| `GET /me` | 200 with valid bearer token; 401/403 with none |
| `PUT /me` | 200, updates both `members` and `member_profiles` fields in one call |
| `GET /dashboard` | 200, `impact_score: null`, `recent_activity: []` |
| `GET /profile/{member_id}` | 200 for any authenticated member viewing another member |
| `GET /chapter/{chapter_id}/members` | 403 for `standard_member`; 200 for `chapter_admin` after role promotion + re-login |

## 5. Authentication Verification

- Access tokens confirmed to carry all 7 required claims
  (`member_id`, `membership_number`, `chapter_id`, `role`, `user_type`,
  `verified`, `active`) via direct `decode_token()` inspection.
- Member tokens are rejected by admin-scoped checks and vice versa (the
  `user_type` claim gate in `get_current_member_claims`).
- Refresh rotation confirmed single-use: reusing a rotated-out refresh
  token is rejected.
- `get_current_member` reloads the member from the database on every
  request rather than trusting token claims — confirmed a deactivated
  member's existing access token no longer results in `is_active: true`
  behavior at the next request (checked directly against the `Member`
  row, not the stale claim).

## 6. Security Verification

| Requirement | Status | Evidence |
|---|---|---|
| Passwords hashed with bcrypt, never stored plaintext | PASS | `hash_password`/`verify_password` reused from `app.core.security`; `members.hashed_password` is the only password column |
| Refresh tokens stored only as hashes | PASS | `member_sessions.refresh_token_hash` is a bcrypt hash of a `secrets.token_urlsafe(48)` value; the raw value exists only in the HTTP response, never persisted |
| SQL injection protection | PASS | Every query goes through SQLAlchemy ORM parameter binding; no raw string-formatted SQL anywhere in this module |
| XSS / input sanitisation | PASS | Free-text fields pass through NFKC normalisation + control-character stripping before persistence |
| Duplicate registration protection | PASS | Partial unique index is the source of truth; pre-check + `IntegrityError` catch as defense in depth — verified both the pre-check path and forced the DB-level constraint independently |
| Timing-attack resistance on login | PASS | `authenticate()` always runs a bcrypt comparison, even for unknown emails, against a fixed dummy hash |

## 7. Test Results

36/36 tests passing (unit + integration), covering every category the
D.2 directive lists: registration, login, refresh, logout, duplicate
email rejection, duplicate membership number prevention (via the
concurrency test below, not just a unit assertion), profile update,
chapter assignment, authentication, authorization (RBAC 403s),
inactive-member rejection, soft-delete behavior, JWT validation,
repository methods, and API endpoints.

```
36 passed in 3.30s
```

**Concurrency test (membership-number generation, not part of the
pytest suite — run separately against a live 20-connection concurrent
load):** 20 threads, each with its own database session, registered
simultaneously against a real PostgreSQL instance.

```
errors: []
total registrations: 20
unique membership numbers: 20
['NDIP-2026-000063', 'NDIP-2026-000064', ..., 'NDIP-2026-000082']
```

Zero errors, zero duplicates, perfectly sequential — the directive's
"transaction safe... no duplicates under concurrent registration"
requirement is empirically verified, not just designed for.

**Coverage target**: the directive asks for 90%+. Coverage was not
measured with a coverage tool (no `pytest-cov` in `requirements.txt`);
36 tests span every method in `member_repository.py` and
`member_service.py` at least once, and every router endpoint including
its error paths, but this is a disclosed gap — see §9.

## 8. Performance Review

- `find_by_id` uses `joinedload` for `chapter` and `profile` to avoid
  N+1 queries on the most common lookup path (`GET /me`, `GET
  /profile/{id}`).
- `search_members` / `list_chapter_members` are offset-paginated with a
  server-enforced max `page_size` of 200.
- No load/stress testing beyond the 20-connection concurrency test in
  §7 was performed — reasonable for a foundation-layer module with zero
  production traffic yet, but flagged for awareness before this module
  carries real load.

## 9. Deviations

Three deviations from the literal D.2 directive. All are disclosed here
and in `PHASE_D2_IMPLEMENTATION.md`; none were silently absorbed.

**9.1 — A fifth table, `member_number_counters`, was added.** The
directive names exactly four tables. A `COUNT(*)`-based membership-number
scheme cannot satisfy "transaction safe... no duplicates under
concurrent registration" (two concurrent transactions can compute the
same count before either commits). A row-locked (`SELECT ... FOR
UPDATE`) per-year counter table is the standard safe pattern and was
added for that reason, then verified under real concurrent load (§7).

**9.2 — Member RBAC does not extend `app/core/rbac.py`.** That module's
`require_permission()` depends on `roles`/`permissions`/
`role_permissions`/`user_roles` tables that have no migration anywhere
in this codebase (confirmed by searching `migrations/`) and whose own
code gracefully degrades to "allow all" when they're missing. Extending
a permission system that currently allows everything would have made
Members Foundation's RBAC a no-op while appearing to enforce access
control — assessed as a worse outcome than building a new, smaller,
equally-reusable dependency (`require_member_role`) against data that
actually exists (`members.role`). Same dependency-factory pattern as
`rbac.py`, different (real) data source.

**9.3 — No admin API for verification/activation/role-promotion, and no
chapter-management CRUD API.** The D.2 directive's Service Layer section
requires `MemberService` methods for account activation and
verification, and its Repository section requires `assign_chapter()` —
all implemented and unit-tested — but its API section lists no
corresponding admin-facing routes, and no route to create/edit a
chapter at all. Four reference chapters are seeded via migration so
chapter assignment is exercisable end-to-end without a chapter-admin
API. Promoting a member to `chapter_admin` for testing purposes required
a direct repository call, not an API request — there is currently no way
for real NDIP staff to do this without database access. This is very
likely intentional scoping (an admin surface for member/chapter
management plausibly belongs to a near-term follow-up), but it means
Members Foundation is not yet operable end-to-end by staff through the
API alone. Flagged for Architect decision on whether this needs
addressing before D.3, or is deferred to its own addendum.

## 10. Outstanding Items Requiring Architect Decision

| Item | Status |
|---|---|
| Admin API for verify/activate/deactivate/promote a member | Open — see §9.3 |
| Chapter management CRUD API | Open — see §9.3 |
| Deploy migration + code to `ndip-backend-1`/`ndip-db-1` | Open — not yet executed against live containers |
| Run `test_members.py` inside `ndip-backend-1` itself | Open — validated independently against a disposable Postgres + real TestClient outside the container (this report); in-container run still pending, same gap noted in Phase D.1 |
| Measure test coverage with a coverage tool | Open — 36 tests span every method at least once, but no `pytest-cov` measurement exists |
| Refresh-token device/IP binding | Open — metadata is stored but not currently checked on refresh; flagged as a future hardening item, not a defect |

## 11. Certification

I certify that the Phase D.2 Members Foundation implementation described
in this report was scoped, built, and validated within the boundaries
set by the directive; that no existing Phase A/B/C/D.1 schema, table, or
API was modified; that the migration is transactional, idempotent, and
contains no destructive statements; that the Phase D.1 production defect
class (ORM/migration schema drift) was proactively closed and verified
by deliberately reproducing the original failure scenario; and that the
membership-number generator's concurrency-safety claim was verified
under real concurrent load rather than asserted. All three deviations
from the literal directive are disclosed in §9. Per the Stop Condition,
implementation work stops here pending your review — no work has begun
on NERS, Sponsorships, Ward CRM, Projects, Opportunities, Intelligence
Graph, Verification, Impact Index, or any other Phase D.3+ module.

**Status: PHASE D.2 IMPLEMENTATION COMPLETE (SANDBOX-VERIFIED) — PENDING
LIVE DEPLOYMENT AND ARCHITECTURAL REVIEW.**
