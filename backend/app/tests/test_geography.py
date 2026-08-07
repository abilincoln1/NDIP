"""
Phase D.1 Geography tests: seed integrity, repository, service search,
and API endpoints.

Run (inside the backend container, after `pip install pytest` — see
PHASE_D1_IMPLEMENTATION.md, pytest is not currently in requirements.txt):

    docker exec ndip-backend-1 python -m pytest app/tests/test_geography.py -v

Note: API-level assertions expect bare lists / objects (response_model=
list[StateOut] etc.), matching the existing participants.py / events.py
convention — not the wrapped {"states": [...]} shape from an earlier
draft of this file.
"""
from app.repositories.geography_repository import GeographyRepository
from app.services.geography_service import GeographyService
from app.models.models import NgState, NgLga


# ─── Seed integrity ─────────────────────────────────────────────────────

def test_seed_has_37_states(db):
    assert db.query(NgState).count() == 37


def test_seed_has_774_lgas(db):
    assert db.query(NgLga).count() == 774


def test_fct_present_as_a_state(db):
    fct = db.query(NgState).filter(NgState.name == "Federal Capital Territory").first()
    assert fct is not None
    assert fct.code == "NG-FC"


def test_fct_has_6_area_councils(db):
    fct = db.query(NgState).filter(NgState.name == "Federal Capital Territory").first()
    lga_count = db.query(NgLga).filter(NgLga.state_id == fct.id).count()
    assert lga_count == 6


def test_every_lga_has_a_valid_state(db):
    orphaned = (
        db.query(NgLga)
        .outerjoin(NgState, NgLga.state_id == NgState.id)
        .filter(NgState.id.is_(None))
        .count()
    )
    assert orphaned == 0


def test_lagos_has_20_lgas(db):
    lagos = db.query(NgState).filter(NgState.name == "Lagos").first()
    assert lagos is not None
    assert db.query(NgLga).filter(NgLga.state_id == lagos.id).count() == 20


# ─── Repository layer ───────────────────────────────────────────────────

def test_repository_list_states_returns_37(db):
    repo = GeographyRepository(db)
    assert len(repo.list_states()) == 37


def test_repository_lgas_by_state_lagos(db):
    repo = GeographyRepository(db)
    lagos = db.query(NgState).filter(NgState.name == "Lagos").first()
    lgas = repo.list_lgas_by_state(lagos.id)
    names = {l.name for l in lgas}
    assert "Ikeja" in names
    assert "Lagos Island" in names
    assert len(lgas) == 20


def test_repository_get_lga_unknown_returns_none(db):
    repo = GeographyRepository(db)
    assert repo.get_lga(999_999) is None


def test_repository_wards_by_lga_empty_until_csv_import(db):
    # No ward data is seeded by the migration on purpose (see
    # PHASE_D1_IMPLEMENTATION.md) — an existing LGA should return an
    # empty list, not error, until scripts/seed_geography_csv.py is run.
    repo = GeographyRepository(db)
    lagos = db.query(NgState).filter(NgState.name == "Lagos").first()
    ikeja = db.query(NgLga).filter(NgLga.state_id == lagos.id, NgLga.name == "Ikeja").first()
    wards = repo.list_wards_by_lga(ikeja.id)
    assert wards == []


def test_repository_search_partial_match_state(db):
    repo = GeographyRepository(db)
    result = repo.search("Lag")
    state_names = {s.name for s in result["states"]}
    assert "Lagos" in state_names


def test_repository_search_partial_match_lga(db):
    repo = GeographyRepository(db)
    result = repo.search("Lagelu")  # Oyo LGA
    lga_names = {l.name for l in result["lgas"]}
    assert "Lagelu" in lga_names


# ─── Service layer (caching wrapper) ─────────────────────────────────────

def test_service_get_states_matches_repository(db):
    service = GeographyService(db)
    states = service.get_states()
    assert len(states) == 37
    assert {"id", "name", "code"} <= set(states[0].keys())


def test_service_get_lgas_by_state_unknown_returns_none(db):
    service = GeographyService(db)
    assert service.get_lgas_by_state(999_999) is None


def test_service_search_short_query_returns_empty(db):
    service = GeographyService(db)
    result = service.search("a")  # below min length of 2
    assert result["states"] == []
    assert result["lgas"] == []
    assert result["wards"] == []


# ─── API endpoints (bare list / object responses via response_model) ────

def test_api_get_states(client):
    resp = client.get("/api/v2/geography/states")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 37


def test_api_get_lgas_valid_state(client, db):
    lagos = db.query(NgState).filter(NgState.name == "Lagos").first()
    resp = client.get(f"/api/v2/geography/lgas/{lagos.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 20
    assert all(l["state_id"] == lagos.id for l in body)


def test_api_get_lgas_unknown_state_404(client):
    resp = client.get("/api/v2/geography/lgas/999999")
    assert resp.status_code == 404


def test_api_get_wards_unknown_lga_404(client):
    resp = client.get("/api/v2/geography/wards/999999")
    assert resp.status_code == 404


def test_api_get_wards_valid_lga_empty_list(client, db):
    lagos = db.query(NgState).filter(NgState.name == "Lagos").first()
    ikeja = db.query(NgLga).filter(NgLga.state_id == lagos.id, NgLga.name == "Ikeja").first()
    resp = client.get(f"/api/v2/geography/wards/{ikeja.id}")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_search_partial_match(client):
    resp = client.get("/api/v2/geography/search", params={"q": "Kan"})
    assert resp.status_code == 200
    body = resp.json()
    state_names = {s["name"] for s in body["states"]}
    lga_names = {l["name"] for l in body["lgas"]}
    assert "Kano" in state_names
    assert "Kankia" in lga_names or "Kankara" in lga_names  # Katsina LGAs matching "Kan"


def test_api_search_requires_query_param(client):
    resp = client.get("/api/v2/geography/search")
    assert resp.status_code == 422  # q is required
