# Phase D.1 — Geography Foundation: Implementation Report

Status: **Deployed and verified live.** Migration applied, 37 states / 774
LGAs confirmed via direct DB query, API endpoints confirmed via live HTTP
requests against `ndip-backend-1`. Members, NERS, Sponsorships, Projects,
Verification, and Impact Index are explicitly out of scope for this phase
and were not touched.

## Tables Added

All additive. No existing Phase A/B/C table was altered, dropped, or
otherwise modified.

| Table | PK | FKs | Purpose |
|---|---|---|---|
| `ng_states` | `id` INTEGER | — | 37 states incl. FCT |
| `ng_lgas` | `id` INTEGER | `state_id → ng_states.id` | 774 LGAs |
| `ng_wards` | `id` INTEGER | `lga_id → ng_lgas.id` | Wards (schema only — see Seed Statistics) |
| `ng_polling_units` | `id` INTEGER | `ward_id → ng_wards.id` | Polling units (schema only) |

## ID Scheme — Read Before Relying On Numeric IDs

`ng_states.id` and `ng_lgas.id` are **NDIP-internal sequential surrogate
keys**, not a reproduction of any single external numbering authority.
INEC, NBS, and NPC each use different, inconsistent numbering schemes for
states and LGAs, and no single canonical "official" integer registry was
available to fetch programmatically during this build.

- `ng_states.id`: 1–36 assigned alphabetically to the 36 states, **37
  assigned explicitly to Federal Capital Territory** (appended, not
  alphabetical — "Federal Capital Territory" would otherwise sort as
  state #15 between Enugu and Gombe). Confirmed live: Lagos = 24.
- `ng_states.code`: the real, externally verifiable **ISO 3166-2:NG**
  code (e.g. `NG-LA` for Lagos, `NG-FC` for FCT). Use this column, not
  `id`, for any external cross-reference.
- `ng_lgas.id`: 1–774, grouped by state (states in the order above), LGAs
  alphabetical within each state.
- `ng_wards.id` / `ng_polling_units.id`: assigned at CSV-import time by
  `scripts/seed_geography_csv.py` — no fixed numbering scheme, since no
  ward/PU data ships in the migration (see below).

## Seed Statistics

- **States: 37/37 seeded** (36 states + FCT). Confirmed via
  `SELECT count(*) FROM ng_states;` against the live `agora_db` → 37.
- **LGAs: 774/774 seeded.** Confirmed the same way → 774, and confirmed
  zero orphaned `state_id` values.
- **Wards / Polling Units: 0 seeded, by design.** Lagos alone has ~13,390
  polling units (INEC figures); Kano ~11,222; Ogun ~5,042; FCT ~2,822.
  Hand-typing this volume of civic administrative data from an LLM's
  memory into a migration risks shipping silently wrong data into a
  platform used for political/civic intelligence. `ng_wards` and
  `ng_polling_units` are fully created with correct schema, FKs, and
  indexes; they're empty until real data is imported via
  `scripts/seed_geography_csv.py` from an authoritative source (INEC
  publications, or the HDX "Nigeria - INEC - LGA and Wards" dataset).

## Routes Added

All under `app/api/routes/geography.py`, registered with prefix
`/api/v2/geography`. **Matches the existing codebase convention exactly**
(see `participants.py`): `response_model=` declared per route, bare
lists/objects returned — not a `{"states": [...]}` wrapper.

| Method | Path | Response | Behavior |
|---|---|---|---|
| GET | `/api/v2/geography/states` | `list[StateOut]` | All 37 states, cached |
| GET | `/api/v2/geography/lgas/{state_id}` | `list[LgaOut]` | LGAs for a state; 404 if state_id doesn't exist; cached |
| GET | `/api/v2/geography/wards/{lga_id}` | `list[WardOut]` | Wards for an LGA; 404 if lga_id doesn't exist; empty list (not an error) if the LGA exists but has no wards imported yet |
| GET | `/api/v2/geography/search?q=&limit=` | `SearchResultOut` | Partial (ILIKE) match across state, LGA, and ward names; `q` shorter than 2 chars returns an empty result set rather than erroring |

Confirmed live: `GET /states` returns 37 items; `GET /search?q=Lag`
correctly returns Lagos (state) plus Lagelu, Lagos Island, and Lagos
Mainland (LGAs).

**Auth assumption:** these routes are *not* behind `get_current_user`,
unlike `watchlist.py` / `participants.py`'s list endpoint — geography
reference data is typically needed to populate public-facing forms (e.g.
during onboarding, before login). If this platform requires every
endpoint authenticated, add `_: dict = Depends(get_current_user)` to
each route.

## Schemas — Corrected Mid-Build

`app/schemas/geography_schemas.py` uses **real pydantic `BaseModel`
classes** with `class Config: from_attributes = True`, exactly matching
`app/schemas/schemas.py`'s existing convention (`ParticipantOut`,
`EventOut`, etc.) and FastAPI's `response_model=` mechanism.

An earlier draft of this file avoided pydantic entirely, based on a
stale assumption (carried over from prior project notes) that pydantic
was broken in this environment. Reading the actual `app/schemas/schemas.py`
file showed dozens of working `BaseModel` classes already in production
use with `response_model=` on routes like `participants.py` — so that
assumption was wrong, and the schema file was rewritten to match reality
before deployment.

## Indexes

- B-tree: `state_id`, `lga_id`, `ward_id` (all FK columns), `name` and
  `code` on every table, plus composite uniques `(state_id, name)` and
  `(lga_id, name)` to prevent duplicate LGA/ward names within a parent.
- Trigram (`pg_trgm` GIN) on `name` for all four tables, for fast partial
  match at scale — created **best-effort**: wrapped in a `DO $$ ...
  EXCEPTION WHEN OTHERS $$` block, so if `pg_trgm` isn't installed on the
  Postgres server, the migration continues and search still works via
  the plain B-tree `name` indexes, just without trigram acceleration.
  (Verified this actually matters: the disposable Postgres instance used
  to validate this migration before deployment didn't have `pg_trgm`
  available at all, and the migration completed cleanly anyway.)

## Migration Bug Found and Fixed During Deployment

The live `ndip-backend-1` container runs with `uvicorn --reload`
(WatchFiles). The moment the new `NgState`/`NgLga`/`NgWard`/
`NgPollingUnit` classes were added to `app/models/models.py`, the
existing `Base.metadata.create_all(bind=engine)` call in `main.py`'s
lifespan hook **auto-created the tables on hot-reload, before the SQL
migration ever ran.**

That's fine for the tables themselves (idempotent `CREATE TABLE IF NOT
EXISTS` in the migration correctly no-ops against them) — but the ORM
column `created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
default=utcnow)` only carries a **Python-side** default (applied by
SQLAlchemy on `.add()`), not a database-level `DEFAULT`. Since the
migration's seed step is raw `INSERT INTO ng_states (id, name, code)
VALUES (...)` — deliberately not going through the ORM — every row hit a
`NOT NULL constraint` violation on `created_at` the first time this ran
in production, rolling back the whole seed transaction (no partial/
corrupt state — Postgres correctly aborted the entire transaction).

**Fix applied:** every `INSERT INTO ng_states` / `INSERT INTO ng_lgas`
line in `migrations/phase_d_00_geography.sql` now explicitly sets
`created_at` to `now()`, so the migration works regardless of whether
the ORM or the migration itself created the table first. Re-validated
against a disposable Postgres instance with the exact failure scenario
reproduced (table pre-created with a `NOT NULL` `created_at` and no
default) before redeploying — confirmed working, then confirmed again
live: `COMMIT`, 37/774 rows, zero nulls.

## Caching

`app/services/geography_service.py` uses the existing
`app.services.cache` module (`get_cached` / `set_cached` / `cache_key` —
same functions `watchlist.py` uses) with two new local TTL constants
(`TTL_GEOGRAPHY_STATES`, `TTL_GEOGRAPHY_LGAS` = 6h each), converted via
`StateOut.model_validate(row).model_dump()` / `LgaOut...` before caching
since the cache layer JSON-serializes everything. No changes were made
to `cache.py` itself. Wards and search are not cached — wards will
change as CSV imports land, and search needs to reflect that
immediately; both are returned as raw ORM rows for the router's
`response_model` to serialize directly.

## Testing

`app/tests/conftest.py` + `app/tests/test_geography.py`: seed-integrity
(state/LGA counts, FCT presence, orphan-FK check), repository, service
(incl. cache round-trip), and API-endpoint tests (200s, 404s,
partial-match search, bare-list/object response shapes matching the
`response_model` convention).

**Before running them:**
1. `pytest` is not currently in `requirements.txt` — install it first:
   `docker exec ndip-backend-1 pip install pytest --break-system-packages`
2. No `tests/` directory existed anywhere in this codebase before this
   phase — these are the first tests in the project.

**Verification performed beyond the test file itself:** I don't have
direct shell access inside `ndip-backend-1`, so before asking for this to
be deployed, I built a disposable PostgreSQL instance in my own sandbox
and ran the actual shipped files (repository, service, schemas, router)
against it end to end via a real FastAPI `TestClient`, in the real
deployment order. This caught two real bugs before they reached
production:
1. The `pg_trgm` exception handler only caught `insufficient_privilege`,
   but a server missing the extension entirely raises
   `FeatureNotSupported` — broadened to `WHEN OTHERS`.
2. The schemas file initially avoided pydantic based on a stale
   assumption — corrected after finding `schemas.py`'s real convention.

A third bug (the `created_at` default issue above) only surfaced during
actual deployment, because it depends on the live container's
hot-reload behavior creating tables via the ORM before the migration
runs — not something reproducible without the real container. Fixed and
re-verified the same way: reproduce the exact failure in a disposable
Postgres instance, confirm the fix, then redeploy.

## Known Assumptions

1. **Numeric ID scheme is NDIP-internal**, not a specific external
   registry — see "ID Scheme" above.
2. **No ward/polling-unit data is seeded.** Schema + CSV pipeline only.
3. **Migration applies via raw SQL (psql), not Alembic.** `alembic.ini`
   exists but no `versions/` directory was found — this codebase's real
   pattern is `Base.metadata.create_all()` for schema, raw SQL for seed
   data. Confirmed live: the ORM auto-created tables via hot-reload
   before the SQL migration ran, and both paths ended up consistent.
4. **No auth on geography endpoints** — see Routes Added.
5. **Repository/service class-based layering is new to this codebase** —
   introduced exactly as specified in the brief, scoped to geography
   only, without changing any existing route's style.
6. **`app/repositories/` is a new package**; `app/schemas/` already
   existed (with `schemas.py`) — `geography_schemas.py` was added
   alongside it, not overwriting anything.

## Deliverables

### Files created
- `migrations/phase_d_00_geography.sql`
- `app/repositories/__init__.py`, `app/repositories/geography_repository.py`
- `app/schemas/geography_schemas.py`
- `app/services/geography_service.py`
- `app/api/routes/geography.py`
- `scripts/seed_geography_csv.py`
- `app/tests/conftest.py`, `app/tests/test_geography.py`
- `PHASE_D1_IMPLEMENTATION.md` (this file)

### Files modified
- `app/models/models.py` — append only, 4 new classes
- `app/main.py` — 2 additive lines (1 import, 1 `include_router`)

### Test results
Full pytest run inside the container was not performed by me directly
(no shell access to `ndip-backend-1` — all deployment happened via you
running commands and pasting output back). What is confirmed, live,
against the actual running system:
- Migration applied successfully: `COMMIT`, 37 states, 774 LGAs, zero
  nulls, idempotent.
- `GET /api/v2/geography/states` → 200, 37 items.
- `GET /api/v2/geography/search?q=Lag` → 200, correctly returns Lagos
  (state) and Lagelu / Lagos Island / Lagos Mainland (LGAs).
- Backend hot-reloaded cleanly through every file change with no
  tracebacks in `docker logs ndip-backend-1`.

Run the actual test suite with:
```
docker exec ndip-backend-1 pip install pytest --break-system-packages
docker exec ndip-backend-1 python -m pytest app/tests/test_geography.py -v
```

### Blockers
- None — Phase D.1 is deployed and live.
- Ward/polling-unit data for Lagos/FCT/Ogun/Kano still requires an
  authoritative CSV (INEC or HDX) to be sourced and imported —
  infrastructure is ready, data is not, by design.
