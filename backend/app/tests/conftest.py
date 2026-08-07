"""
Shared fixtures for Phase D.1 geography tests.

No existing tests/ directory or pytest fixture convention exists anywhere
in this codebase yet (checked: `find /app -path '*/tests/*'` returned
nothing) — this is the first test suite. These fixtures run against the
real dev database (agora_db) rather than a separate test DB, since none
exists; that's fine here because states/LGAs are static reference data
(read-only in these tests) and wards/PUs are cleaned up after any test
that writes them.

Place this file at: app/tests/conftest.py (or tests/conftest.py,
whichever your pytest rootdir convention prefers — see
PHASE_D1_IMPLEMENTATION.md for the exact path assumption).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
