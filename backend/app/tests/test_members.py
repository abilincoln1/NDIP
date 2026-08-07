"""
Phase D.2 Members Foundation tests: registration, authentication, refresh
rotation, logout, duplicate rejection, profile/chapter management,
soft delete, JWT claim shape, repository methods, and API endpoints
(including RBAC 403s).

Run (inside the backend container, pytest already required — see
PHASE_D1_IMPLEMENTATION.md for the `pip install pytest` step):

    docker exec ndip-backend-1 python -m pytest app/tests/test_members.py -v

Uses the same `client` / `db` fixtures as test_geography.py
(app/tests/conftest.py) — no separate test database exists in this
codebase, so these tests run against the real dev DB. All rows they
create are identified by a dedicated test email domain (TEST_DOMAIN
below) and hard-deleted in an autouse teardown fixture, so repeated runs
don't accumulate garbage. The public API only exposes soft delete, by
design — this raw cleanup is a test-only concern, not something the app
itself does.
"""
import uuid

import pytest

from app.core.security import decode_token
from app.models.chapter import Chapter
from app.models.member import Member
from app.models.member_profile import MemberProfile
from app.models.member_session import MemberSession
from app.repositories.member_repository import MemberRepository
from app.services.member_service import (
    MemberService,
    DuplicateEmailError,
    WeakPasswordError,
    InvalidCredentialsError,
    InactiveAccountError,
    NotFoundError,
)

TEST_DOMAIN = "ndip-d2-test-sandbox.com"  # NOT example.com/.org/.net, .test, .invalid,
# .local, or .localhost — pydantic's EmailStr (email-validator) rejects all
# RFC 2606 special-use domains/TLDs even with deliverability checking off.
# Found via sandbox validation before deployment — a test-harness detail,
# not a bug in the shipped registration/login code.
STRONG_PASSWORD = "Str0ngPassw0rd!"


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@{TEST_DOMAIN}"


@pytest.fixture(autouse=True)
def _cleanup_test_members(db):
    yield
    ids = [m.id for m in db.query(Member).filter(Member.email.like(f"%@{TEST_DOMAIN}")).all()]
    if ids:
        db.query(MemberSession).filter(MemberSession.member_id.in_(ids)).delete(synchronize_session=False)
        db.query(MemberProfile).filter(MemberProfile.member_id.in_(ids)).delete(synchronize_session=False)
        db.query(Member).filter(Member.id.in_(ids)).delete(synchronize_session=False)
        db.commit()


@pytest.fixture()
def lagos_chapter(db):
    chapter = db.query(Chapter).filter(Chapter.name == "Lagos Chapter").first()
    assert chapter is not None, "Expected seed chapter 'Lagos Chapter' from phase_d_02_members.sql"
    return chapter


def _register(service: MemberService, **overrides) -> tuple:
    fields = {
        "email": unique_email(),
        "password": STRONG_PASSWORD,
        "full_name": "Test Member",
    }
    fields.update(overrides)
    return service.register(**fields)


# ─── Registration ────────────────────────────────────────────────────────

def test_registration_creates_member_with_membership_number(db):
    service = MemberService(db)
    member, access_token, refresh_token = _register(service)
    assert member.membership_number.startswith("NDIP-")
    parts = member.membership_number.split("-")
    assert len(parts) == 3 and len(parts[2]) == 6
    assert member.role == "standard_member"
    assert member.is_active is True
    assert member.is_verified is False
    assert access_token and refresh_token


def test_registration_creates_profile_row(db):
    service = MemberService(db)
    member, _, _ = _register(service)
    repo = MemberRepository(db)
    profile = repo.get_profile(member.id)
    assert profile is not None
    assert profile.member_id == member.id


def test_membership_numbers_are_sequential_within_year(db):
    service = MemberService(db)
    _, _, _ = _register(service)
    m2, _, _ = _register(service)
    m3, _, _ = _register(service)
    n2 = int(m2.membership_number.split("-")[-1])
    n3 = int(m3.membership_number.split("-")[-1])
    assert n3 == n2 + 1


def test_registration_rejects_duplicate_email(db):
    service = MemberService(db)
    email = unique_email()
    _register(service, email=email)
    with pytest.raises(DuplicateEmailError):
        _register(service, email=email)


def test_registration_rejects_weak_password(db):
    service = MemberService(db)
    with pytest.raises(WeakPasswordError):
        _register(service, password="weak")


def test_registration_rejects_unknown_chapter(db):
    service = MemberService(db)
    with pytest.raises(NotFoundError):
        _register(service, chapter_id=uuid.uuid4())


def test_registration_accepts_valid_chapter(db, lagos_chapter):
    service = MemberService(db)
    member, _, _ = _register(service, chapter_id=lagos_chapter.id)
    assert member.chapter_id == lagos_chapter.id


# ─── Authentication ──────────────────────────────────────────────────────

def test_login_success_returns_tokens(db):
    service = MemberService(db)
    email = unique_email()
    _register(service, email=email)
    member, access_token, refresh_token = service.authenticate(email=email, password=STRONG_PASSWORD)
    assert member.email == email
    assert access_token and refresh_token


def test_login_wrong_password_rejected(db):
    service = MemberService(db)
    email = unique_email()
    _register(service, email=email)
    with pytest.raises(InvalidCredentialsError):
        service.authenticate(email=email, password="WrongPassword1")


def test_login_unknown_email_rejected(db):
    service = MemberService(db)
    with pytest.raises(InvalidCredentialsError):
        service.authenticate(email=unique_email(), password=STRONG_PASSWORD)


def test_login_inactive_member_rejected(db):
    service = MemberService(db)
    email = unique_email()
    member, _, _ = _register(service, email=email)
    service.deactivate_member(member)
    with pytest.raises(InactiveAccountError):
        service.authenticate(email=email, password=STRONG_PASSWORD)


# ─── Refresh / logout ────────────────────────────────────────────────────

def test_refresh_rotates_token_and_invalidates_old_one(db):
    service = MemberService(db)
    email = unique_email()
    _register(service, email=email)
    _, _, refresh_token = service.authenticate(email=email, password=STRONG_PASSWORD)

    new_access, new_refresh = service.refresh(refresh_token)
    assert new_access and new_refresh
    assert new_refresh != refresh_token

    with pytest.raises(InvalidCredentialsError):
        service.refresh(refresh_token)  # old token is single-use


def test_refresh_with_garbage_token_rejected(db):
    service = MemberService(db)
    with pytest.raises(InvalidCredentialsError):
        service.refresh("not-a-real-token")


def test_logout_revokes_session(db):
    service = MemberService(db)
    email = unique_email()
    _register(service, email=email)
    _, _, refresh_token = service.authenticate(email=email, password=STRONG_PASSWORD)

    service.logout(refresh_token)

    with pytest.raises(InvalidCredentialsError):
        service.refresh(refresh_token)  # revoked, can no longer be used


def test_logout_is_silent_on_invalid_token(db):
    service = MemberService(db)
    service.logout("garbage")  # must not raise


# ─── Profile / chapter management ────────────────────────────────────────

def test_update_me_updates_member_and_profile_fields(db):
    service = MemberService(db)
    member, _, _ = _register(service)
    updated = service.update_me(member, {"phone": "+2348000000000", "occupation": "Engineer"})
    assert updated.phone == "+2348000000000"
    profile = service.get_profile(updated)
    assert profile.occupation == "Engineer"


def test_assign_chapter_success(db, lagos_chapter):
    service = MemberService(db)
    member, _, _ = _register(service)
    updated = service.assign_chapter(member, lagos_chapter.id)
    assert updated.chapter_id == lagos_chapter.id


def test_assign_chapter_unknown_raises(db):
    service = MemberService(db)
    member, _, _ = _register(service)
    with pytest.raises(NotFoundError):
        service.assign_chapter(member, uuid.uuid4())


def test_verify_member_sets_flag(db):
    service = MemberService(db)
    member, _, _ = _register(service)
    assert member.is_verified is False
    verified = service.verify_member(member)
    assert verified.is_verified is True


def test_dashboard_returns_placeholders(db):
    service = MemberService(db)
    member, _, _ = _register(service)
    dashboard = service.get_dashboard(member)
    assert dashboard["impact_score"] is None
    assert dashboard["recent_activity"] == []
    assert dashboard["verification_status"] == "unverified"
    assert dashboard["member_summary"]["membership_number"] == member.membership_number


# ─── Soft delete ─────────────────────────────────────────────────────────

def test_soft_deleted_member_not_found_by_email(db):
    service = MemberService(db)
    email = unique_email()
    member, _, _ = _register(service, email=email)
    repo = MemberRepository(db)
    repo.soft_delete_member(member)
    db.commit()

    assert repo.find_by_email(email) is None
    assert repo.find_by_email(email, include_deleted=True) is not None


def test_soft_deleted_email_can_be_reused(db):
    service = MemberService(db)
    email = unique_email()
    member, _, _ = _register(service, email=email)
    repo = MemberRepository(db)
    repo.soft_delete_member(member)
    db.commit()

    # Same email, new registration — allowed because the unique index is
    # partial (WHERE deleted_at IS NULL). This is the behavior the partial
    # index was specifically designed to enable.
    member2, _, _ = _register(service, email=email)
    assert member2.id != member.id


# ─── JWT claim shape ──────────────────────────────────────────────────────

def test_access_token_contains_required_claims(db, lagos_chapter):
    service = MemberService(db)
    member, access_token, _ = _register(service, chapter_id=lagos_chapter.id)
    claims = decode_token(access_token)
    for key in ("member_id", "membership_number", "chapter_id", "role", "user_type", "verified", "active"):
        assert key in claims
    assert claims["user_type"] == "member"
    assert claims["member_id"] == str(member.id)
    assert claims["chapter_id"] == str(lagos_chapter.id)


# ─── Repository layer ─────────────────────────────────────────────────────

def test_repository_find_by_membership_number(db):
    service = MemberService(db)
    member, _, _ = _register(service)
    repo = MemberRepository(db)
    found = repo.find_by_membership_number(member.membership_number)
    assert found is not None and found.id == member.id


def test_repository_search_members_by_name(db):
    marker = uuid.uuid4().hex[:8]
    service = MemberService(db)
    _register(service, full_name=f"Searchable {marker} One")
    _register(service, full_name=f"Searchable {marker} Two")
    repo = MemberRepository(db)
    result = repo.search_members(q=marker)
    assert result["total"] == 2


def test_repository_list_chapter_members(db, lagos_chapter):
    service = MemberService(db)
    _register(service, chapter_id=lagos_chapter.id)
    repo = MemberRepository(db)
    result = repo.list_chapter_members(lagos_chapter.id)
    assert result["total"] >= 1
    assert all(m.chapter_id == lagos_chapter.id for m in result["items"])


# ─── API endpoints ─────────────────────────────────────────────────────────

def test_api_register_and_login(client, db):
    email = unique_email()
    resp = client.post(
        "/api/v2/members/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "API Test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["member"]["email"] == email
    assert "access_token" in body and "refresh_token" in body

    login_resp = client.post("/api/v2/members/login", json={"email": email, "password": STRONG_PASSWORD})
    assert login_resp.status_code == 200


def test_api_register_duplicate_email_returns_409(client, db):
    email = unique_email()
    payload = {"email": email, "password": STRONG_PASSWORD, "full_name": "API Test"}
    client.post("/api/v2/members/register", json=payload)
    resp = client.post("/api/v2/members/register", json=payload)
    assert resp.status_code == 409


def test_api_login_wrong_password_returns_401(client, db):
    email = unique_email()
    client.post("/api/v2/members/register", json={"email": email, "password": STRONG_PASSWORD, "full_name": "X"})
    resp = client.post("/api/v2/members/login", json={"email": email, "password": "WrongPassword1"})
    assert resp.status_code == 401


def test_api_me_requires_auth(client):
    resp = client.get("/api/v2/members/me")
    assert resp.status_code in (401, 403)


def test_api_me_and_dashboard_with_valid_token(client, db):
    email = unique_email()
    reg = client.post(
        "/api/v2/members/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "API Test"},
    ).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    me_resp = client.get("/api/v2/members/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email

    dash_resp = client.get("/api/v2/members/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    assert dash_resp.json()["impact_score"] is None


def test_api_put_me_updates_profile(client, db):
    email = unique_email()
    reg = client.post(
        "/api/v2/members/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "API Test"},
    ).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    put_resp = client.put("/api/v2/members/me", headers=headers, json={"phone": "+15550001111"})
    assert put_resp.status_code == 200
    assert put_resp.json()["phone"] == "+15550001111"


def test_api_refresh_and_logout(client, db):
    email = unique_email()
    reg = client.post(
        "/api/v2/members/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "API Test"},
    ).json()

    refresh_resp = client.post("/api/v2/members/refresh", json={"refresh_token": reg["refresh_token"]})
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()

    logout_resp = client.post("/api/v2/members/logout", json={"refresh_token": new_tokens["refresh_token"]})
    assert logout_resp.status_code == 204

    # Using the now-revoked refresh token again must fail.
    second_refresh = client.post("/api/v2/members/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert second_refresh.status_code == 401


def test_api_chapter_members_forbidden_for_standard_member(client, db, lagos_chapter):
    email = unique_email()
    reg = client.post(
        "/api/v2/members/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "API Test", "chapter_id": str(lagos_chapter.id)},
    ).json()
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    resp = client.get(f"/api/v2/members/chapter/{lagos_chapter.id}/members", headers=headers)
    assert resp.status_code == 403


def test_api_chapter_members_allowed_for_chapter_admin(client, db, lagos_chapter):
    email = unique_email()
    reg = client.post(
        "/api/v2/members/register",
        json={"email": email, "password": STRONG_PASSWORD, "full_name": "Admin Test", "chapter_id": str(lagos_chapter.id)},
    ).json()

    # Promote to chapter_admin directly (no public API exposes role
    # promotion in this phase — see PHASE_D2_IMPLEMENTATION.md "Known
    # Limitations") and re-login so the new token carries the updated role.
    repo = MemberRepository(db)
    member = repo.find_by_email(email)
    repo.update_member(member, role="chapter_admin")
    db.commit()

    login_resp = client.post("/api/v2/members/login", json={"email": email, "password": STRONG_PASSWORD})
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = client.get(f"/api/v2/members/chapter/{lagos_chapter.id}/members", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_api_profile_view_by_other_authenticated_member(client, db):
    email_a = unique_email()
    email_b = unique_email()
    reg_a = client.post(
        "/api/v2/members/register",
        json={"email": email_a, "password": STRONG_PASSWORD, "full_name": "Member A"},
    ).json()
    reg_b = client.post(
        "/api/v2/members/register",
        json={"email": email_b, "password": STRONG_PASSWORD, "full_name": "Member B"},
    ).json()

    headers_a = {"Authorization": f"Bearer {reg_a['access_token']}"}
    resp = client.get(f"/api/v2/members/profile/{reg_b['member']['id']}", headers=headers_a)
    assert resp.status_code == 200
