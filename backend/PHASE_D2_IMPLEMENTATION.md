# Phase D.2 — Members Foundation: Implementation Report

Status: **Deployed to sandbox and fully verified; awaiting deployment to
the live NDIP dev environment and formal architectural review before
D.3.** Every claim below marked "confirmed" was verified against a real
PostgreSQL 16.2 instance and a real FastAPI `TestClient` running the
actual shipped code — not asserted from a design document. Deployment
steps to `ndip-backend-1` / `ndip-db-1` are in §12; per the D.2 directive's
Stop Condition, no code for NERS, Sponsorships, Ward CRM, Projects,
Opportunities, Intelligence Graph, Verification, or Impact Index was
started.

## 1. Architecture

Members Foundation follows the repository → service → schema → router
layering established in Phase D.1 (`app/repositories/geography_repository.py`
→ `app/services/geography_service.py`), extended here with a fifth
concern the geography module didn't need: authentication.

```
HTTP request
  → app/api/routes/members.py        (FastAPI router — request/response only)
  → app/core/member_rbac.py          (JWT verification + role gate, as a dependency)
  → app/services/member_service.py   (business logic: passwords, tokens,
                                       membership numbers, validation)
  → app/repositories/member_repository.py  (SQL only — no business logic)
  → PostgreSQL (members, chapters, member_profiles, member_sessions,
                member_number_counters)
```

The service layer raises plain Python exceptions
(`DuplicateEmailError`, `WeakPasswordError`, `InvalidCredentialsError`,
`InactiveAccountError`, `NotFoundError`) and never imports FastAPI —
`app/api/routes/members.py` is the only place these become HTTP status
codes. This means the service layer is independently testable (see §10)
without spinning up the ASGI app.

Authentication reuses `app/core/security.py` as-is: `hash_password`,
`verify_password` (bcrypt), `create_access_token`, `decode_token`
(python-jose, HS256). No second authentication framework was introduced.
Member tokens are distinguished from admin tokens by a `"user_type":
"member"` JWT claim.

## 2. Database Schema

Migration: `migrations/phase_d_02_members.sql`. Additive only — no
`ALTER`, no `DROP`, no modification of any existing table. Wrapped in a
single `BEGIN`/`COMMIT`. Idempotent (`CREATE TABLE IF NOT EXISTS`,
`CREATE INDEX IF NOT EXISTS`, `ON CONFLICT DO NOTHING`) — confirmed by
running it twice against the same database with identical row counts
both times.

| Table | PK | Notes |
|---|---|---|
| `chapters` | UUID | Soft delete, partial-unique `name` |
| `members` | UUID | Soft delete, partial-unique `email` and `membership_number` |
| `member_profiles` | UUID | 1:1 with `members` via unique FK, cascades on delete |
| `member_sessions` | UUID | Refresh-token sessions, cascades on delete |
| `member_number_counters` | `year` (INTEGER) | Support table — see §6 |

UUID primary keys use PostgreSQL's native `gen_random_uuid()` — built
into Postgres core since v13, **no extension required**. Verified this
directly against a disposable PostgreSQL 16.2 instance (matching the
production `postgres:16-alpine` image) before writing a single line of
the migration, rather than assuming it.

**A fifth table beyond the four named in the D.2 directive —
`member_number_counters` — was added.** This is disclosed here and in
`PHASE_D2_COMPLIANCE_REPORT.md` rather than silently introduced; the
rationale is in §6.

### Cross-module foreign keys (read-only references, nothing modified)
- `chapters.state_id → ng_states.id` (Phase D.1)
- `members.state_of_origin_id → ng_states.id`, `members.lga_of_origin_id → ng_lgas.id` (Phase D.1)
- `members.admin_user_id → admin_users.id ON DELETE SET NULL` (Phase A)
- `members.chapter_id → chapters.id`

### Soft-delete-aware uniqueness
`chapters.name`, `members.email`, and `members.membership_number` are
enforced unique via **partial unique indexes** (`WHERE deleted_at IS
NULL`), not plain unique constraints. This means a soft-deleted chapter's
name or a soft-deleted member's email can be reused by a new row — a
deliberate choice, since the alternative (permanently blocking reuse) has
no clear benefit and would make account closure + re-registration
impossible. Confirmed via `test_soft_deleted_email_can_be_reused`.

### The Phase D.1 lesson, applied proactively
Phase D.1 shipped a real production bug: `uvicorn --reload` created the
new ORM tables via `Base.metadata.create_all()` *before* the SQL
migration ran, and the ORM's `created_at` column had no database-level
default — only a Python-side one — so the migration's raw `INSERT`
statements hit a `NOT NULL` violation.

Every table in this module sets `server_default=text("now()")` for
`created_at`/`updated_at` and `server_default=text("gen_random_uuid()")`
for `id`, in both the ORM models **and** the raw SQL migration,
byte-for-byte matching. **Reproduced the exact Phase D.1 failure
scenario on purpose** — called `Base.metadata.create_all()` against a
disposable database first, then ran the SQL migration second — and
confirmed it no-ops cleanly with zero errors, regardless of which one
runs first. See §11.

## 3. Entity Relationships

```
ng_states (D.1) ──┐
                   ├──< chapters
ng_lgas (D.1) ─────┤         │
                   │         │ 1
admin_users (A) ───┤         │
        │ 0..1     │         │ 0..*
        ▼          ▼         ▼
      members ───────────< members (chapter_id FK)
        │ 1
        │
        ├──1:1── member_profiles
        │
        └──1:*── member_sessions
```

`members.state_of_origin_id` / `lga_of_origin_id` are independent FKs
into the Phase D.1 geography tables (a member's *origin*, distinct from
their chapter's location).

## 4. Authentication Flow

**Registration** (`POST /register`): validates email uniqueness (partial
index + pre-check), password strength, optional chapter existence →
generates a membership number (§6) → hashes password with bcrypt →
creates `members` + `member_profiles` rows → issues an access token and
refresh token directly (does **not** re-run the password check it just
performed — see the docstring on `MemberService.register`, this avoids
doubling the bcrypt cost of every signup for no security benefit).

**Login** (`POST /login`): looks up by email, verifies password. Always
runs a bcrypt comparison even when the email doesn't exist (`verify_password`
against a fixed dummy hash) so response timing doesn't leak which emails
are registered — the D.2 directive's "timing attacks" requirement.

**Access tokens**: JWT (HS256, `app.core.security`), 30-minute expiry
(`MEMBER_ACCESS_TOKEN_EXPIRE_MINUTES`, local to the service — admin
tokens keep their existing 24-hour default). Payload:

```json
{
  "sub": "<member id>", "member_id": "<member id>",
  "membership_number": "NDIP-2026-000001",
  "chapter_id": "<uuid or null>", "role": "standard_member",
  "user_type": "member", "verified": false, "active": true,
  "exp": 1234567890
}
```
Confirmed live via `test_access_token_contains_required_claims`.

**Refresh tokens**: *not* JWTs. An opaque random secret
(`secrets.token_urlsafe(48)`) is bcrypt-hashed and stored in
`member_sessions.refresh_token_hash` — the raw value is never persisted,
matching the D.2 directive's "store only hashes." The token returned to
the client is `"<session_id>.<raw_secret>"`, so `refresh()`/`logout()`
can find the exact session row in O(1) instead of re-hashing against
every active session (bcrypt is deliberately slow by design). 30-day
expiry. **Refresh is rotating**: each use revokes the presented session
and issues a new one — confirmed the old token is rejected on reuse
(`test_refresh_rotates_token_and_invalidates_old_one`).

**Logout**: revokes the session behind the given refresh token. Silent
(never raises) on an already-invalid token, since logging out twice
should never be an error.

**Freshness over convenience**: `get_current_member` (in
`app/core/member_rbac.py`) reloads the member from the database on every
request rather than trusting the `role`/`active`/`verified` claims baked
into the access token at issuance. If an admin deactivates a member or
changes their role mid-session, it takes effect immediately — not after
the 30-minute token happens to expire.

## 5. Repository Pattern

`app/repositories/member_repository.py` — database access only, per the
D.2 directive ("no business logic"). Every method takes/returns plain
values or ORM objects; none of it knows what a password is, what a JWT
is, or what "NDIP-2026-000001" means. Covers `members`, `chapters`
(read-side), `member_profiles`, `member_sessions`, and the counter table
— kept in one file because the directive names exactly one repository
file.

## 6. Service Layer

`app/services/member_service.py` owns all business rules: password
policy, sanitisation, membership-number formatting, token issuance/
rotation, and every state transition (verify, activate, deactivate,
assign chapter).

### Membership Number Generation
Format `NDIP-YYYY-000001`, sequential per year, generated by
`MemberRepository.lock_and_increment_counter(year)`:

```sql
SELECT last_value FROM member_number_counters WHERE year = :year FOR UPDATE;
-- increment, UPDATE, in the same transaction as the member INSERT
```

`SELECT ... FOR UPDATE` row-locks the single counter row for `year`, so
concurrent registrations serialize on that one row instead of racing on
a `COUNT(*)`-derived number (which is not safe under concurrency — two
transactions could both compute the same "next" number before either
commits). This is why `member_number_counters` exists as a fifth table:
a naive scheme cannot satisfy the directive's explicit "transaction
safe... no duplicates under concurrent registration" requirement.

**Verified, not assumed**: ran 20 concurrent registrations from 20
separate database connections against a real PostgreSQL instance. Result:
20/20 succeeded, zero errors, 20 unique sequential membership numbers
(`NDIP-2026-000063` through `NDIP-2026-000082` in one run). See
`PHASE_D2_COMPLIANCE_REPORT.md` §7 for the raw output.

### Input sanitisation
Free-text fields (`full_name`, `phone`, `residence_country`, profile
fields) pass through `_sanitize_text()`: Unicode NFKC normalisation and
stripping of control characters (Unicode category `C*`), which removes
the most common injection vectors for a JSON API without mangling
legitimate accented names. SQL injection is not a concern anywhere in
this module — every query goes through the SQLAlchemy ORM's parameter
binding; no raw string-formatted SQL exists in this module.

## 7. API Documentation

Prefix `/api/v2/members` (matches the `/api/v2/geography` convention
from Phase D.1).

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/register` | none | Returns tokens + `MemberResponse` immediately |
| POST | `/login` | none | Timing-safe on unknown email |
| POST | `/refresh` | refresh token in body | Rotates; old token rejected after use |
| POST | `/logout` | refresh token in body | 204, idempotent/silent on bad input |
| GET | `/me` | member bearer token | |
| PUT | `/me` | member bearer token | Splits payload across `members` + `member_profiles` |
| GET | `/dashboard` | member bearer token | `impact_score`/`recent_activity` are explicit placeholders |
| GET | `/profile/{member_id}` | member bearer token | Any authenticated member — see assumption below |
| GET | `/chapter/{chapter_id}/members` | `chapter_admin`/`national_director`/`super_admin` only | Paginated |

**Two access-policy assumptions, not specified in the directive:**
`GET /profile/{member_id}` allows any authenticated member to view
another member's profile (no sensitive fields are exposed — no password
hash, no session data). `GET /chapter/{chapter_id}/members` is
role-gated because a full roster is more sensitive than a single
profile. Both are disclosed for Architect confirmation.

## 8. RBAC

Seven roles per the directive: `super_admin`, `national_director`,
`chapter_admin`, `verified_member`, `standard_member`, `verifier`,
`intelligence_analyst`. `members.role` (default `standard_member`)
drives a reusable FastAPI dependency factory,
`require_member_role(*roles)` in `app/core/member_rbac.py` — no
per-endpoint hardcoded checks.

**Why this is a new file rather than extending `app/core/rbac.py`:**
the existing `require_permission()` resolves roles via `roles`,
`permissions`, `role_permissions`, and `user_roles` tables. None of
those tables have a migration anywhere in this codebase — confirmed by
searching every file in `migrations/`. `rbac.py`'s own code catches the
resulting query failure and falls back to "allow all"
(`except Exception: return {}` → `if not role_permissions: return True`).
That system is a scaffold running in permissive/degraded mode today, not
a populated permission store, and it's keyed to `admin_users` (staff), a
different identity space from members. Building member RBAC on tables
that don't exist would silently produce permission checks that always
pass — worse than no check. Member roles are instead resolved directly
from `members.role`, re-loaded from the database on every request (see
§4, "freshness over convenience"). This is the same dependency-factory
*shape* as `rbac.py`, just resolving against data that actually exists.

## 9. Migration Process

`migrations/phase_d_02_members.sql` — manual `psql` execution against
`ndip-db-1`, following the exact process used for Phase D.1 (no Alembic
versions exist in this codebase; `alembic.ini` is present but unused).
Transactional, idempotent, additive-only — see §2.

## 10. Indexes

| Column | Table | Type |
|---|---|---|
| `email` | members | Unique, partial (`deleted_at IS NULL`) |
| `membership_number` | members | Unique, partial |
| `chapter_id`, `state_of_origin_id`, `lga_of_origin_id`, `is_active`, `admin_user_id` | members | B-tree |
| `name` | chapters | Unique, partial |
| `country`, `state_id`, `status` | chapters | B-tree |
| `member_id`, `expires_at`, `revoked_at` | member_sessions | B-tree |

All match the D.2 directive's explicit index list, plus the partial
unique indexes needed for soft-delete-aware uniqueness (§2).

## 11. Performance Considerations

`MemberRepository.find_by_id` uses `joinedload(Member.chapter,
Member.profile)` to avoid N+1 queries when returning a member with its
chapter and profile in one response. `search_members` and
`list_chapter_members` are offset-paginated with a bounded `page_size`
(max 200, enforced by the `Query` validator in the router) rather than
returning unbounded result sets.

The hot-reload/migration-ordering regression from Phase D.1 was
reproduced deliberately in a disposable environment before deployment
(see §2) — this is a correctness/performance-adjacent concern (a failed
migration mid-deployment is a worse outage than any query-plan issue)
and is called out here because it's the single most consequential
lesson carried forward from the previous phase.

## 12. Deployment Instructions

1. Confirm `ndip-backend-1` picks up the new files (bind-mounted volume;
   `uvicorn --reload` hot-reloads automatically — watch `docker logs
   ndip-backend-1` for a clean reload with no tracebacks).
2. Apply the migration against `ndip-db-1`:
   ```powershell
   docker cp C:\Projects\NDIP\backend\migrations\phase_d_02_members.sql ndip-db-1:/tmp/phase_d_02_members.sql
   docker exec -e PGPASSWORD=agora_pass ndip-db-1 psql -U agora_user -d agora_db -f /tmp/phase_d_02_members.sql
   ```
3. Verify:
   ```powershell
   docker exec -e PGPASSWORD=agora_pass ndip-db-1 psql -U agora_user -d agora_db -c "SELECT count(*) FROM chapters; SELECT count(*) FROM members; SELECT count(*) FROM member_number_counters;"
   ```
   Expect `chapters = 4` (seed rows), `members = 0` until real
   registrations occur.
4. Exercise the API:
   ```powershell
   Invoke-RestMethod -Method Post http://localhost:8000/api/v2/members/register -ContentType "application/json" -Body '{"email":"smoke-test@ndip-smoke.example","password":"Str0ngPassw0rd!","full_name":"Smoke Test"}'
   ```
   Expect `201` with `access_token`, `refresh_token`, and `member.membership_number`
   starting `NDIP-2026-`.
5. Install pytest if not already present (see Phase D.1 note — not in
   `requirements.txt`) and run:
   ```powershell
   docker exec ndip-backend-1 pip install pytest --break-system-packages
   docker exec ndip-backend-1 python -m pytest app/tests/test_members.py -v
   ```

## 13. Known Limitations

1. **No admin API for role promotion, verification, or activation.**
   `MemberService.verify_member`, `activate_member`, and
   `deactivate_member` exist and are unit-tested, but the D.2 directive's
   API list has no admin-management endpoints — only self-service member
   routes. Promoting a member to `chapter_admin` currently requires a
   direct database update (this is exactly how
   `test_api_chapter_members_allowed_for_chapter_admin` exercises it).
   This is very likely intentional — a member-management admin surface
   plausibly belongs to a future phase — but it means Members Foundation
   is not yet operable end-to-end by staff without direct DB access.
2. **No chapter-management CRUD API.** The directive's endpoint list has
   no way to create/edit/retire a chapter, but `GET
   /chapter/{chapter_id}/members` and `assign_chapter()` need chapters to
   exist. Four reference chapters ship as seed data in the migration
   (Lagos, Abuja/FCT, Diaspora–US, Diaspora–UK) so the feature is
   exercisable; real chapter administration needs its own future
   endpoint set.
3. **`impact_score` and `recent_activity` in the dashboard are hardcoded
   placeholders** (`None` / `[]`), exactly as instructed — Impact Index
   is out of scope for this phase.
4. **Refresh tokens are bearer secrets with no device binding beyond the
   `ip_address`/`device`/`user_agent` metadata stored at issuance** (not
   currently checked against on refresh). Session hijacking via a leaked
   refresh token isn't detected beyond the existing single-use rotation.
   Worth a future hardening pass (e.g., flag/revoke-all on IP mismatch).
5. **The dev/test environment has no separate test database** — see
   Phase D.1's note, unchanged here. `test_members.py` runs against the
   real dev DB and hard-deletes its own rows in an autouse teardown
   fixture, identified by a dedicated test email domain.

## 14. Future Integration Points

- **NERS / Sponsorships / Projects / Opportunities**: will need
  `members.id` as an actor reference — the UUID PK and `role`/
  `membership_tier` fields were chosen with this in mind.
- **Verification**: `members.is_verified` is a boolean placeholder today;
  a real verification phase will likely add a `member_verifications`
  table and a documented flow, replacing the current
  `MemberService.verify_member()` no-op-beyond-a-flag.
- **Impact Index**: `get_dashboard()`'s placeholder fields
  (`impact_score`, `recent_activity`) are the intended integration seam.
- **Admin member-management API**: §13 item 1 is the clearest gap for a
  near-term follow-up phase (or an addendum to D.2) before this module is
  fully operable without direct database access.
