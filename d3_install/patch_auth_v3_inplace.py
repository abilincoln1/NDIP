"""
Patches auth_v3.py in-place inside the container.
Fixes /me route and refresh route to handle missing memberships table.
Run: docker exec ndip-backend-1 python3 /tmp/patch_auth_v3_inplace.py
"""
TARGET = '/app/app/api/routes/auth_v3.py'

with open(TARGET, 'r') as f:
    c = f.read()

# --- Fix 1: /me route memberships query ---
old1 = '''    # Memberships across all tenants
    memberships = db.execute(
        text("""
            SELECT m.id, m.tenant_id, t.name AS tenant_name, t.slug,
                   o.name AS org_name, m.membership_number,
                   m.membership_type, m.status, m.joined_date
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            LEFT JOIN organisations o ON o.id = m.organisation_id
            WHERE m.identity_id = :id AND m.status = 'active'
        """),
        {"id": current["sub"]}
    ).fetchall()'''

new1 = '''    # Memberships across all tenants — safe fallback before D5A-S3
    memberships = []
    try:
        memberships = db.execute(
            text("""
                SELECT m.id, m.tenant_id, t.name AS tenant_name, t.slug,
                       o.name AS org_name, m.membership_number,
                       m.membership_type, m.status, m.joined_date
                FROM memberships m
                JOIN tenants t ON t.id = m.tenant_id
                LEFT JOIN organisations o ON o.id = m.organisation_id
                WHERE m.identity_id = :id AND m.status = 'active'
            """),
            {"id": current["sub"]}
        ).fetchall()
    except Exception:
        db.rollback()
        memberships = []'''

if old1 in c:
    c = c.replace(old1, new1)
    print("Fix 1 applied: /me memberships query")
else:
    print("Fix 1 already applied or pattern not found")

# --- Fix 2: login route membership lookup ---
old2 = '''    # 5. Resolve membership and roles for this tenant
    membership = db.execute(
        text("""
            SELECT m.id, m.status
            FROM memberships m
            WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
            LIMIT 1
        """),
        {"iid": str(identity.id), "tid": tenant_id}
    ).fetchone()

    roles = []
    if membership:
        role_rows = db.execute(
            text("""
                SELECT kr.name
                FROM membership_roles mr
                JOIN kernel_roles kr ON kr.id = mr.role_id
                WHERE mr.membership_id = :mid
            """),
            {"mid": str(membership.id)}
        ).fetchall()
        roles = [r.name for r in role_rows]'''

new2 = '''    # 5. Resolve membership and roles — safe fallback before D5A-S3
    roles = []
    try:
        membership = db.execute(
            text("""
                SELECT m.id, m.status
                FROM memberships m
                WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
                LIMIT 1
            """),
            {"iid": str(identity.id), "tid": tenant_id}
        ).fetchone()
        if membership:
            role_rows = db.execute(
                text("""
                    SELECT kr.name
                    FROM membership_roles mr
                    JOIN kernel_roles kr ON kr.id = mr.role_id
                    WHERE mr.membership_id = :mid
                """),
                {"mid": str(membership.id)}
            ).fetchall()
            roles = [r.name for r in role_rows]
    except Exception:
        db.rollback()
        roles = []'''

if old2 in c:
    c = c.replace(old2, new2)
    print("Fix 2 applied: login membership lookup")
else:
    print("Fix 2 already applied or pattern not found")

# --- Fix 3: refresh route membership lookup ---
old3 = '''    # Rebuild roles
    membership = db.execute(
        text("""
            SELECT m.id FROM memberships m
            WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
            LIMIT 1
        """),
        {"iid": identity_id, "tid": tenant_id}
    ).fetchone()

    roles = []
    if membership:
        role_rows = db.execute(
            text("""
                SELECT kr.name FROM membership_roles mr
                JOIN kernel_roles kr ON kr.id = mr.role_id
                WHERE mr.membership_id = :mid
            """),
            {"mid": str(membership.id)}
        ).fetchall()
        roles = [r.name for r in role_rows]'''

new3 = '''    # Rebuild roles — safe fallback before D5A-S3
    roles = []
    try:
        membership = db.execute(
            text("""
                SELECT m.id FROM memberships m
                WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
                LIMIT 1
            """),
            {"iid": identity_id, "tid": tenant_id}
        ).fetchone()
        if membership:
            role_rows = db.execute(
                text("""
                    SELECT kr.name FROM membership_roles mr
                    JOIN kernel_roles kr ON kr.id = mr.role_id
                    WHERE mr.membership_id = :mid
                """),
                {"mid": str(membership.id)}
            ).fetchall()
            roles = [r.name for r in role_rows]
    except Exception:
        db.rollback()
        roles = []'''

if old3 in c:
    c = c.replace(old3, new3)
    print("Fix 3 applied: refresh membership lookup")
else:
    print("Fix 3 already applied or pattern not found")

with open(TARGET, 'w') as f:
    f.write(c)

print(f"\nDone. Watchfiles will auto-reload.")
print(f"memberships=[] occurrences: {c.count('memberships = []')}")
