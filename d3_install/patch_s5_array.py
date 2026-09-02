"""
Patch projects_v3.py to fix ANY(:org_ids) array parameter handling.
SQLAlchemy named params don't support Python lists as PG arrays directly.
Solution: use string formatting for the array or use IN clause.
Run: docker exec ndip-backend-1 python3 /tmp/patch_s5_array.py
"""
import subprocess

TARGET = '/app/app/api/routes/projects_v3.py'

with open(TARGET, 'r') as f:
    content = f.read()

# Fix 1: get_participant_org_ids — return as comma-separated string for SQL
# Fix 2: list_projects — replace ANY(:org_ids) with dynamic IN clause
# Fix 3: can_access_project — same fix

# Replace the get_participant_org_ids function to return list of strings
old_func = '''def get_participant_org_ids(db: Session, identity_id: str) -> list:
    """Get all organisation IDs where this identity has active membership."""
    rows = db.execute(text("""
        SELECT DISTINCT organisation_id FROM memberships
        WHERE identity_id = :iid AND status = 'active'
    """), {"iid": identity_id}).fetchall()
    return [str(r.organisation_id) for r in rows if r.organisation_id]'''

new_func = '''def get_participant_org_ids(db: Session, identity_id: str) -> list:
    """Get all organisation IDs where this identity has active membership."""
    rows = db.execute(text("""
        SELECT DISTINCT organisation_id FROM memberships
        WHERE identity_id = :iid AND status = 'active'
    """), {"iid": identity_id}).fetchall()
    return [str(r.organisation_id) for r in rows if r.organisation_id]


def build_org_in_clause(org_ids: list) -> str:
    """Build a safe IN clause for org_ids — UUIDs only, no injection risk."""
    if not org_ids:
        return "('00000000-0000-0000-0000-000000000000')"
    # Validate UUID format before embedding
    import re
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    safe = [oid for oid in org_ids if uuid_pattern.match(oid.lower())]
    if not safe:
        return "('00000000-0000-0000-0000-000000000000')"
    return "(" + ",".join(f"'{oid}'" for oid in safe) + ")"'''

content = content.replace(old_func, new_func)

# Fix list_projects — replace ANY(:org_ids) with dynamic IN
old_list = '''    # Visibility-aware filter
    filters.append("""(
        p.tenant_id = :tid
        OR (p.tenant_id IS NULL AND p.visibility = 'public')
        OR (p.tenant_id IS NULL AND p.visibility IN ('participating_orgs','tenant') AND EXISTS (
            SELECT 1 FROM project_participants pp
            WHERE pp.project_id = p.id AND pp.status = 'active'
            AND (pp.identity_id = :iid OR pp.organisation_id = ANY(:org_ids))
        ))
        OR (p.tenant_id IS NULL AND p.visibility = 'private' AND (
            p.created_by = :iid OR EXISTS (
                SELECT 1 FROM project_participants pp
                WHERE pp.project_id = p.id AND pp.status = 'active'
                AND pp.identity_id = :iid
            )
        ))
    )""")

    if status:'''

new_list = '''    # Visibility-aware filter — build dynamic org IN clause (no SQLAlchemy array issue)
    org_in = build_org_in_clause(my_org_ids)
    filters.append(f"""(
        p.tenant_id = :tid
        OR (p.tenant_id IS NULL AND p.visibility = 'public')
        OR (p.tenant_id IS NULL AND p.visibility IN ('participating_orgs','tenant') AND EXISTS (
            SELECT 1 FROM project_participants pp
            WHERE pp.project_id = p.id AND pp.status = 'active'
            AND (pp.identity_id = :iid OR pp.organisation_id IN {org_in})
        ))
        OR (p.tenant_id IS NULL AND p.visibility = 'private' AND (
            p.created_by = :iid OR EXISTS (
                SELECT 1 FROM project_participants pp
                WHERE pp.project_id = p.id AND pp.status = 'active'
                AND pp.identity_id = :iid
            )
        ))
    )""")

    if status:'''

content = content.replace(old_list, new_list)

# Remove :org_ids from params since it's now inlined
old_params = '''    params = {
        "tid": tenant_id,
        "iid": identity_id,
        "org_ids": org_ids_sql,
    }'''

new_params = '''    params = {
        "tid": tenant_id,
        "iid": identity_id,
    }'''

content = content.replace(old_params, new_params)

# Remove org_ids_sql line
content = content.replace(
    '    org_ids_sql = my_org_ids if my_org_ids else ["00000000-0000-0000-0000-000000000000"]\n',
    ''
)

# Fix can_access_project — replace ANY(:org_ids) with dynamic IN
old_access = '''        part = db.execute(text("""
            SELECT id FROM project_participants
            WHERE project_id = :pid AND status = 'active'
            AND (
                identity_id = :iid
                OR organisation_id = ANY(:org_ids)
            )
        """), {
            "pid": str(project.id),
            "iid": identity_id,
            "org_ids": my_org_ids or ["00000000-0000-0000-0000-000000000000"]
        }).fetchone()'''

new_access = '''        org_in2 = build_org_in_clause(my_org_ids)
        part = db.execute(text(f"""
            SELECT id FROM project_participants
            WHERE project_id = :pid AND status = 'active'
            AND (
                identity_id = :iid
                OR organisation_id IN {org_in2}
            )
        """), {
            "pid": str(project.id),
            "iid": identity_id,
        }).fetchone()'''

content = content.replace(old_access, new_access)

with open(TARGET, 'w') as f:
    f.write(content)

r = subprocess.run(['python3', '-m', 'py_compile', TARGET], capture_output=True, text=True)
print(f'Syntax check: {"PASS" if r.returncode == 0 else r.stderr}')

# Verify fixes applied
checks = [
    ('build_org_in_clause defined', 'def build_org_in_clause' in content),
    ('org_in used in list filter', 'org_in = build_org_in_clause' in content),
    ('org_in2 used in can_access', 'org_in2 = build_org_in_clause' in content),
    ('ANY(:org_ids) removed', 'ANY(:org_ids)' not in content),
]
for label, result in checks:
    print(f'  {"OK" if result else "FAIL"}: {label}')

print('Done. Watchfiles will auto-reload.')
