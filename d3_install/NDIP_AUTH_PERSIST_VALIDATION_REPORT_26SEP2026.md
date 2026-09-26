# NDIP — Real-Data Operational Validation & Auth Persistence Report
**To:** Chief Solutions Architect
**From:** Chief Engineering AI (Claude)
**Date:** 26 September 2026
**Directive:** NDIP-AUTH-PERSIST-001 / Real-Data Operational Validation

---

## 1. Final Git Commit Hash

Auth persistence committed at: `129f019`
(`backend/app/api/routes/auth_v3.py` with v2_compat patch)

Platform currently at: `5836354` (daily ops report)
All source files confirmed in git.

---

## 2. Authentication Persistence Result

**PASS**

| Check | Result |
|---|---|
| v2_compat patch in Windows source | ✓ Confirmed (`findstr "v2_compat"` returned match) |
| v2_compat patch committed to git | ✓ Confirmed at `129f019` |
| Patch present in rebuilt container after clean restart | ✓ `grep -c "v2_compat" auth_v3.py` returned `1` |
| v2 member token accepted on v3 routes | ✓ Confirmed |

The patch permanently maps v2 member tokens → platform_identities for v3 route access. It survives container rebuild from source.

---

## 3. Clean Restart Result

**PASS**

Full `docker compose down` → `docker compose up -d` cycle performed. 

| Check | Result |
|---|---|
| Backend health (`/health`) | ✓ `status: ok` |
| Database intact | ✓ D5A-S6, 21 activities |
| No data loss | ✓ All records preserved |
| No schema change | ✓ Confirmed |
| No volume deletion | ✓ Confirmed |

---

## 4. Activities UI Result

**PASS** — 21 records returned via API after clean restart. v2 token accepted.

---

## 5. Volunteers UI Result

**PASS** — 8 records returned via API after clean restart.

---

## 6. Projects UI Result

**PASS** — 13 records returned via API after clean restart.

---

## 7. First Genuine Historical Record Result

**PASS**

**Record:** Tinubu-Wike Day Rally — Birmingham
**ID:** `789bfa9f-48f9-42b9-a4f1-5fca499f45f9`

| Field | Value | Verified |
|---|---|---|
| Title | Tinubu-Wike Day Rally - Birmingham | ✓ |
| Date | 2026-09-25 | ✓ |
| Activity type | meeting | ✓ |
| Location | 042 Restaurant and Bar, 129 Soho Hill, Birmingham B19 1AT | ✓ |
| Description | Full description preserved including 8:00 p.m. timing note | ✓ |
| Recorded by | NDIP National Director | ✓ |
| Tenant | RTIFN (10000000-...) | ✓ |
| Status | Draft | ✓ |
| is_verified | False | ✓ |
| Fabricated data | None | ✓ |

**Schema observation:** The Activity schema does not contain a dedicated `start_time` field. The actual start time (20:00) has been preserved in the description field as instructed. This is noted as a schema limitation for architect awareness — no schema change was made.

---

## 8. Number of Genuine Records Entered

**10 genuine RTIFN engagement records** now in the platform:

| Date | Event |
|---|---|
| 04/07/2026 | APCUK 2nd Anniversary Celebration |
| 19/07/2026 | Renewed Hope Ambassadors-Diaspora UK Inauguration, Catford |
| 19/07/2026 | RTIFN Birmingham Committee Meeting, Smethwick |
| 24/07/2026 | National Diaspora Day 2026 — Virtual participation |
| 25/07/2026 | RTIFN Birmingham Chapter Meeting — 12 members, NDIP presented |
| 03/08/2026 | AMBO Procession — Trafalgar Square to Nigerian High Commission |
| 29/08/2026 | APC UK Leicestershire Caucus Inauguration, Leicester |
| 30/08/2026 | APC UK 2027 Campaign Council Inauguration |
| 18/09/2026 | APC Emergency Stakeholders Meeting, Birmingham |
| **25/09/2026** | **Tinubu-Wike Day Rally, Birmingham** (entered this session) |

All records: verification_status = **Draft** (self-reported). No false verification.

---

## 9. Genuine Defects Discovered

| Defect | Severity | Status |
|---|---|---|
| Container network issue on restart (`db` hostname not resolving) | Medium | Resolved by running `docker compose down` + `docker compose up -d` as a unit — not separately |
| v2 token stored in localStorage not refreshed after restart | Low | Resolved by hard-refresh or sign-out/in — browser cache issue |

No schema or API defects discovered during real-data entry.

---

## 10. Usability Observations

| Observation | Nature |
|---|---|
| No start_time field on Activity | Schema limitation — noted, not blocking |
| Activity type dropdown requires exact type name match | Minor — "meeting" appropriate for the rally record |
| Location text field accepts free text correctly | Working well |
| Description field handles multi-sentence text correctly | Working well |
| Draft status clearly shown on retrieval | Working correctly |
| Birmingham location not resolvable to ward level | Expected — Birmingham is UK, not Nigerian ward geography |

**Enhancement suggestions (not implemented):**
- Start time field on Activity (future schema consideration for S7/S9)
- UK location support (currently geographic cascade is Nigeria-only)
- Participant count field for meetings/rallies

---

## 11. Data Fields Unavailable in Current Model

| Field | Status |
|---|---|
| `start_time` / `time_of_day` | Not in schema — retained in description |
| Attendance count for this record | Not supplied by project owner — not fabricated |
| Ward-level location (UK) | Not applicable — Nigerian ward geography only |

---

## 12. S7 Confirmation

**S7 was NOT implemented.** No evidence_items, verification_events, evidence storage, attachment infrastructure, or new verification state machine was created.

---

## 13. Schema/API Confirmation

**No schema changes were made.** No new API endpoints were created. No backend architecture changes. The auth_v3.py v2_compat addition was already authorised and committed — it was persisted to Windows source only, no new logic added.

---

## 14. Final Recommendation

**STOP — Acceptance criteria satisfied.**

All 14 acceptance criteria from the directive are met:

✓ v2_compat patch permanently in Windows source and git
✓ Clean restart does not remove the patch
✓ Authentication survives restart
✓ Activities, Volunteers, Projects work after clean restart
✓ 25 September 2026 engagement entered through API
✓ Record retrieved successfully
✓ Description preserved exactly
✓ Draft/self-reported status preserved
✓ No fabricated data introduced
✓ Tenant isolation verified
✓ No direct DB writes
✓ No RLS weakening
✓ No false verification
✓ No database reset, volume deletion, or schema change

The platform is operational with 10 genuine RTIFN engagement records. Handing back to Chief Solutions Architect for next directive.

---

*Chief Engineering AI — NDIP on Orion Platform Kernel*
*26 September 2026 | Commit: 5836354 | Platform: D5A-S6*
