"""
Patch auth_v3.py to accept v2 member tokens on v3 routes.
When a v2 token is presented, look up the platform_identity by email
and return a compatible payload.
Run: docker exec ndip-backend-1 python3 /tmp/patch_v3_auth.py
"""
import subprocess

TARGET = '/app/app/api/routes/auth_v3.py'

with open(TARGET) as f:
    content = f.read()

if 'v2_compat' in content:
    print('Already patched')
    exit(0)

old = '''def get_current_v3_identity(request: Request, db: Session = Depends(get_db)) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth[7:]
    payload = _decode_v3_token(token)
    if payload.get("v") != "3":
        raise HTTPException(status_code=401, detail="Use v3 token for v3 routes")
    identity_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not identity_id or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    # Set RLS session variable
    db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})
    return payload'''

new = '''def get_current_v3_identity(request: Request, db: Session = Depends(get_db)) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth[7:]
    payload = _decode_v3_token(token)

    # v2_compat: accept v2 member tokens by mapping member -> platform_identity
    if payload.get("v") != "3":
        # Try to resolve via member_id or sub from v2 token
        member_id = payload.get("member_id") or payload.get("sub")
        if not member_id:
            raise HTTPException(status_code=401, detail="Use v3 token for v3 routes")
        # Look up platform_identity by matching member email
        row = db.execute(text("""
            SELECT pi.id, pi.email, t.id as tenant_id, t.slug as tenant_slug
            FROM members m
            JOIN platform_identities pi ON pi.email = m.email
            JOIN tenants t ON t.slug = 'rtifn'
            WHERE m.id = :mid
            LIMIT 1
        """), {"mid": member_id}).fetchone()
        if not row:
            # Try by email in v2 token
            email = payload.get("email")
            if email:
                row = db.execute(text("""
                    SELECT pi.id, pi.email, t.id as tenant_id, t.slug as tenant_slug
                    FROM platform_identities pi
                    JOIN tenants t ON t.slug = 'rtifn'
                    WHERE pi.email = :email
                    LIMIT 1
                """), {"email": email}).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Use v3 token for v3 routes")
        # Build compatible payload
        compat_payload = {
            "sub": str(row.id),
            "tenant_id": str(row.tenant_id),
            "tenant_slug": row.tenant_slug,
            "roles": [payload.get("role", "standard_member")],
            "admin_level": None,
            "v": "3_compat",
        }
        db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": str(row.tenant_id)})
        return compat_payload

    identity_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not identity_id or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    # Set RLS session variable
    db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})
    return payload'''

if old in content:
    content = content.replace(old, new)
    with open(TARGET, 'w') as f:
        f.write(content)
    r = subprocess.run(['python3', '-m', 'py_compile', TARGET], capture_output=True, text=True)
    print(f'Syntax: {"PASS" if r.returncode == 0 else r.stderr}')
    print('v2_compat patch applied — v2 tokens now accepted on v3 routes')
else:
    print('Pattern not found — checking current function:')
    for i, line in enumerate(content.split('\n')[94:115], 95):
        print(f'{i}: {line}')
