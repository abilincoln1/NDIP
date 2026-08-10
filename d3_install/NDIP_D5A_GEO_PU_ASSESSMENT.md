# D5A-GEO-PU — Polling Unit Geographic Resolution
# Source & Acquisition Assessment
**Prepared by:** Chief Engineering AI (Claude)
**Submitted to:** Chief Solutions Architect
**Date:** 10 August 2026
**Status:** RESEARCH ONLY — no import authorised

---

## 1. Authoritative Source

**Primary authoritative source: INEC (Independent National Electoral Commission)**

INEC is the constitutional body responsible for voter registration and elections in Nigeria. It is the sole authoritative source for polling unit geography. All polling unit records derive their legitimacy from INEC's official register.

INEC provides polling unit data through two primary interfaces:

**Interface 1 — Polling Unit Locator (inecnigeria.org)**
URL: `https://www.inecnigeria.org/polling-units/`
Navigation: State → LGA → Ward → Polling Unit
Format: Interactive web tool — no bulk download available directly
Status: Live and operational

**Interface 2 — INEC CVR Portal (cvr.inecnigeria.org)**
URL: `https://cvr.inecnigeria.org/pu`
Purpose: Continuous voter registration portal with PU locator
Format: Interactive — State/LGA/Ward/PU dropdown selection
Status: Live and operational

**Interface 3 — INEC Election Results Portal (inecelectionresults.ng / IREV)**
URL: `https://www.inecelectionresults.ng/`
Purpose: Published 2023 General Election results at polling-unit level
Format: Web interface with ward/PU breakdown — confirms 176,846 PU count
Status: Live — last upload recorded April 2024

**Interface 4 — INEC Result Analysis / Downloads**
URL: `https://www.inecnigeria.org/result-analysis/`
Purpose: "Low-level downloadable data for researchers"
Format: Described as available but requires investigation — bulk format unconfirmed
Status: Requires direct engagement with INEC

---

## 2. Published Polling Unit Count

<cite index="14-1">Nigeria has 176,846 polling units. This figure was established following the creation of an additional 56,872 polling units, with 749 polling units also relocated from private properties, palaces, shrines, churches and mosques.</cite>

State-level breakdown (selected):
- Lagos: 13,390
- Kano: 11,222
- Kaduna: 8,012
- Oyo: 6,390
- Ogun: 5,042

<cite index="14-1">Zonal totals: North West 41,671 | South West 34,868 | North Central 27,514 | South South 27,126 | North East 24,806 | South East 21,631.</cite>

---

## 3. Data Fields Available (from INEC sources)

Based on research of the INEC PU Locator and IREV portal, the following fields are available per polling unit:

| Field | Source | Notes |
|---|---|---|
| State name | INEC PU Locator | Text |
| LGA name | INEC PU Locator | Text |
| Registration Area / Ward name | INEC PU Locator | = Ward in NDIP hierarchy |
| Polling Unit name | INEC PU Locator | Text description |
| Polling Unit code | INEC IREV | Format: `SS/LL/WW/PPP` (e.g. `29/09/04/009`) |
| Ward code | INEC IREV | Embedded in PU code |
| GPS coordinates | Third-party reconciliation only | Not confirmed from INEC directly |

**INEC PU code format:** `{State}/{LGA}/{Ward}/{PU}` — a structured hierarchical code that maps directly to the NDIP geography hierarchy.

---

## 4. Machine-Readable Dataset Availability

**Official INEC bulk dataset:** No confirmed bulk-downloadable CSV or JSON file is currently available from INEC's public website. The `result-analysis` page describes downloadable data for researchers but the format and availability require direct engagement with INEC.

**Third-party derived dataset:** <cite index="12-1">An open-source scraper (`JayCodist/inec-polling-units-scraper`) extracts polling unit data from the official INEC website at `https://www.inecnigeria.org/polling-units/`. It produces individual state JSON files with state, LGA, ward and polling unit data, with a summary confirming 37 states, 774 LGAs, 8,809 wards and 176,846 polling units.</cite>

This scraper-derived dataset is useful for reconciliation and development preparation. It must not be treated as the authoritative source for production ingestion.

---

## 5. Source Identifiers

INEC uses a structured PU code as the primary identifier:

```
Format: {State_Code}/{LGA_Code}/{Ward_Code}/{PU_Code}
Example: 29/09/04/009
         ↑  ↑  ↑  ↑
         │  │  │  └── Polling Unit number (3 digits)
         │  │  └───── Ward number within LGA (2 digits)
         │  └──────── LGA number within State (2 digits)
         └─────────── State code (2 digits)
```

This code structure maps directly to the NDIP hierarchy: `ng_states → ng_lgas → ng_wards → ng_polling_units`.

---

## 6. Versioning and Update Mechanism

This is a critical architectural consideration. INEC's own published material confirms that polling unit geography changes over time:

- 2021: 56,872 voting points converted to full polling units
- 2021: 749 polling units relocated from inappropriate locations
- Future elections may trigger further changes

INEC publishes changes through official announcements and updated directories. There is no confirmed automated change-feed or versioned API.

**Implication for NDIP:** The `ng_polling_units` table must support versioning — specifically `effective_date`, `superseded_date`, and `source_version` fields — so that historical activity records remain correctly linked to the polling unit geography that was current at the time of the activity.

---

## 7. Licensing and Provenance Considerations

INEC data is published by a Nigerian federal government body. Civic use of electoral geography data for organisational intelligence, community engagement tracking, and project management is consistent with the platform's stated purpose. NDIP must not use polling unit data for voter targeting, political preference inference, or individual political profiling.

Third-party scraped datasets (including the ward dataset used in T1/T1A) carry no explicit licence. They are derived from INEC's public interface and are suitable for reconciliation but not as a sole source of record.

---

## 8. Recommended Import Strategy

**Phase 1 — Architecture (now, no data load):**
- Preserve `ng_polling_units` table schema
- Add `effective_date`, `superseded_date`, `source_version`, `inec_pu_code` columns
- Add `location_polling_unit_id` as nullable FK to `activities` table (additive, non-breaking)
- Define `geographic_data_provenance` model

**Phase 2 — Source acquisition (before D5A-GEO-PU):**
- Engage INEC directly or via their result analysis portal for bulk machine-readable dataset
- Evaluate the scraper-derived dataset for reconciliation use
- Confirm GPS coordinate availability and provenance

**Phase 3 — D5A-GEO-PU implementation (separate architect directive required):**
1. Validate INEC source — version, date, coverage
2. Reconcile against existing ng_states / ng_lgas / ng_wards
3. Parse INEC PU codes to extract state/LGA/ward/PU components
4. Map to NDIP internal IDs
5. Detect duplicates and orphans
6. Import in batches with transaction safety
7. Verify: 176,846 PUs, 0 orphans, correct state/LGA/ward linkage
8. Run geographic query regression tests
9. Commit baseline

---

## 9. Geographic Data Provenance Model

For polling units (and future geographic enrichments), NDIP should maintain a provenance record:

```sql
CREATE TABLE geographic_data_provenance (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    geographic_level TEXT NOT NULL,  -- 'state','lga','ward','polling_unit'
    ndip_record_id  TEXT NOT NULL,   -- FK to the relevant geo table
    source_org      TEXT NOT NULL,   -- 'INEC'
    source_url      TEXT,
    source_document TEXT,
    source_version  TEXT,
    source_date     DATE,
    acquisition_date DATE NOT NULL DEFAULT CURRENT_DATE,
    source_identifier TEXT,         -- e.g. INEC PU code
    validation_status TEXT DEFAULT 'pending',
    reconciliation_status TEXT DEFAULT 'pending',
    last_verified_date DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

This table is not an S4 deliverable — it is recommended for D5A-GEO-PU. The architecture must reserve space for it.

---

## 10. Summary Assessment

| Item | Assessment |
|---|---|
| Authoritative source | INEC (inecnigeria.org, cvr.inecnigeria.org) |
| Fallback/reconciliation source | `JayCodist/inec-polling-units-scraper` (derived from INEC) |
| Expected record count | 176,846 |
| INEC PU code format | `SS/LL/WW/PPP` — hierarchical, maps to NDIP geo hierarchy |
| Bulk machine-readable dataset | Not confirmed publicly — requires INEC engagement |
| GPS coordinates | Not confirmed from INEC directly |
| Versioning requirement | HIGH — PU geography changes between elections |
| Import complexity | HIGH — 176,846 records, versioning, reconciliation |
| Recommended implementation stage | D5A-GEO-PU — separate directive required |
| S4 blocker | NO — ward resolution is sufficient for S4 |
| Architecture ready | YES — `ng_polling_units` table exists, FK stub needed in activities |

---

## 11. Immediate Actions (No Import Required)

The following schema preparation items can be applied at S4 without importing any PU data:

1. Add `location_polling_unit_id INT REFERENCES ng_polling_units(id)` as nullable column to `activities` table — additive, non-breaking, future-proofs the activity model.
2. Document `ng_polling_units` table schema and confirm it is sufficient for the eventual import.
3. Register D5A-GEO-PU as a named planned extension in the architecture.

No bulk import. No synthetic data. No third-party data treated as authoritative.

---

*Chief Engineering AI — NDIP on Orion Platform Kernel*
*10 August 2026*
*Read-only research — no database changes*
