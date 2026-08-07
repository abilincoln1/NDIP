# NDIP Phase D5 — Pilot Backup Report
**Prepared by:** Chief Engineering AI (Claude, Cowork)
**Date:** 03 August 2026
**Approved scope:** Founder Pilot database baseline (Deliverable 2 of 10)
**Baseline file:** `d3_install/NDIP_D5_PILOT_BASELINE.sql`
**Created:** 2026-08-03 15:10 (Windows host timestamp)

---

## Baseline Creation

| Step | Status | Detail |
|---|---|---|
| pg_dump executed | COMPLETE | `docker exec ndip-db-1 pg_dump -U agora_user -d agora_db -f /tmp/NDIP_D5_PILOT_BASELINE.sql` |
| File transfer to host | COMPLETE | `docker cp ndip-db-1:/tmp/NDIP_D5_PILOT_BASELINE.sql` |
| Baseline file created | COMPLETE | `NDIP_D5_PILOT_BASELINE.sql` at `C:\Projects\NDIP\d3_install\` |
| Script used | `d3_install/run_d5_baseline.bat` (new — the D5 baseline did not exist prior to this session despite the 02 Aug handover implying it did; see certification report for that correction) |

## Baseline File Integrity

| Property | Value |
|---|---|
| File size | 9,228,614 bytes (~9.2 MB) |
| SHA-256 | `fc4bb07673399c398f331bf00f1b6b94ab06d74979fd7ccdf4a2b74cbe4057b4` |
| Format | Plain SQL (`pg_dump` logical dump, PostgreSQL 16.14) |
| Line count | 44,580 |
| Tables in dump | 60 (matches live `agora_db` table count and D2.5 baseline) |

Retain the SHA-256 checksum alongside the file — it's the fastest way to confirm the baseline hasn't been altered before a restore.

## Baseline Contents (row counts at time of creation)

| Table | Rows |
|---|---|
| members | 17 (7 active test accounts + 10 cohort, including Adun's corrected email) |
| chapters | 1 (RTIFN Birmingham) |
| ng_states | 37 |
| ng_lgas | 774 |
| audit_log | 1 |

Row counts pulled live via `psql` immediately after the dump — see `d3_install/NDIP_D5_PILOT_BASELINE_METADATA.txt` for raw output. Only 5 tables were sampled for the metadata file (the ones most relevant to pilot state); the dump itself contains all 60 tables in full.

**Comparison to D2.5 baseline:** table count unchanged (60). Member count unchanged (17). The meaningful difference versus D2.5 is state, not schema: Osazemen Adun's email is now real (`osazadun@gmail.com`) rather than a placeholder, SECRET_KEY has been rotated to its production value, and rate limits are at production settings — none of which show up as row-count deltas but are captured in this session's Pre-Pilot Security Certification report.

## Restore Procedure

```
# Create restore target (if needed) — must connect via an existing database (agora_db),
# NOT bare `-U agora_user` with no -d, which fails: psql defaults to a database
# named after the user ("agora_user"), which does not exist.
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "CREATE DATABASE agora_db_restore;"

# Restore
docker cp NDIP_D5_PILOT_BASELINE.sql ndip-db-1:/tmp/
docker exec ndip-db-1 psql -U agora_user -d agora_db_restore -f /tmp/NDIP_D5_PILOT_BASELINE.sql

# Verify
docker exec ndip-db-1 psql -U agora_user -d agora_db_restore -c "SELECT COUNT(*) FROM members;"
```

**Verified 03 Aug 2026:** the original form of this command (`psql -U agora_user -c ...` with no `-d`) was tested and failed with `FATAL: database "agora_user" does not exist`. The corrected form above was then run end to end against `agora_db_restore`: all 60 tables, sequences, indexes, and constraints restored without error, and `SELECT COUNT(*) FROM members` on the restored copy returned 17 — matching the source database exactly. Full restore procedure is confirmed working.

To restore directly over the live database instead of a side-by-side target (e.g. rolling back a failed pilot stage):

```
docker exec ndip-db-1 psql -U agora_user -d agora_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker cp NDIP_D5_PILOT_BASELINE.sql ndip-db-1:/tmp/
docker exec ndip-db-1 psql -U agora_user -d agora_db -f /tmp/NDIP_D5_PILOT_BASELINE.sql
```

**Caution:** the direct-restore path is destructive — it drops and rebuilds the live schema. Only use it as a deliberate rollback, and only after confirming the current live state should not be preserved.

## Recovery Time Estimate

- Backup creation: ~5–10 seconds (development-scale database, 9.2 MB)
- Restore: ~10–15 seconds
- Application container restart after restore: ~15 seconds
- **Total estimated RTO: < 2 minutes**

## Limitations

- Logical dump (`pg_dump`), not a physical/WAL backup — no point-in-time recovery
- No automated backup schedule — this and the D2.5 baseline are both manual, one-off snapshots
- File is stored locally at `C:\Projects\NDIP\d3_install\` — not replicated to any remote backup store
- For GCP migration: recommend Cloud SQL automated backups with point-in-time recovery, as already noted in the D4 SAT evidence pack

## Sign-off

| Item | Status |
|---|---|
| Baseline created | COMPLETE |
| Integrity checksum recorded | COMPLETE |
| Restore procedure documented, corrected, and tested end to end | COMPLETE — verified against `agora_db_restore`, all 60 tables + 17 members restored correctly |
| Recommendation | Baseline is sufficient to proceed to Stage 1 Internal Validation. Take a fresh baseline again immediately before Stage 2 invitations go out, since cohort/member state will have changed further by then. Drop the `agora_db_restore` test database (`docker exec ndip-db-1 psql -U agora_user -d agora_db -c "DROP DATABASE agora_db_restore;"`) once you're done — it's a test artifact from this verification, not part of the pilot. |
