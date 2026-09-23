# Fix frontend login endpoint
# Changes /auth/login to /api/v2/members/login in api.ts

path = '/app/src/lib/api.ts'
with open(path) as f:
    content = f.read()

old = 'api.post("/auth/login", { email, password })'
new = 'api.post("/api/v2/members/login", { email, password })'

if new in content:
    print('Already patched')
elif old in content:
    fixed = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(fixed)
    print('Patched successfully')
    # Verify
    with open(path) as f:
        for i, line in enumerate(f, 1):
            if 'members/login' in line or ('auth/login' in line and 'post' in line):
                print(f'Line {i}: {line.rstrip()}')
else:
    print('Pattern not found — showing post lines:')
    for i, line in enumerate(content.split('\n'), 1):
        if '.post(' in line and 'login' in line:
            print(f'Line {i}: {line.rstrip()}')
