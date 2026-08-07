"""
Fixes the SAT runner by injecting a properly-indented Redis flush
after the rate limit test block.
Run: docker exec ndip-backend-1 python3 /tmp/patch_sat_runner2.py
"""
TARGET = '/tmp/sat_host_runner_v2.py'

with open(TARGET, 'r') as f:
    lines = f.readlines()

# Remove the broken injection from previous patch (lines with the malformed block)
cleaned = []
skip = False
for line in lines:
    if '# Flush Redis after rate limit test' in line:
        skip = True
    if skip and line.strip() == '':
        skip = False
        continue
    if not skip:
        cleaned.append(line)

# Find the rate limit test end — look for the check() call with "Rate limiting fires"
insert_after = None
for i, line in enumerate(cleaned):
    if 'Rate limiting fires' in line:
        # Find the end of this statement (closing paren on its own line or same line)
        for j in range(i, min(i+5, len(cleaned))):
            if cleaned[j].rstrip().endswith(')'):
                insert_after = j
                break
        break

if insert_after is None:
    print("Could not find insertion point")
    for i, l in enumerate(cleaned[145:165], 145):
        print(f"{i}: {l}", end='')
else:
    # Detect indentation from surrounding lines
    indent = '    '  # default
    for line in cleaned[insert_after-2:insert_after+1]:
        stripped = line.lstrip()
        if stripped:
            indent = line[:len(line)-len(stripped)]
            break

    flush_lines = [
        f'\n',
        f'{indent}# Flush Redis after rate limit test to prevent contaminating subsequent tests\n',
        f'{indent}try:\n',
        f'{indent}    import redis as _redis_flush\n',
        f'{indent}    import os as _os_flush\n',
        f'{indent}    _rf = _redis_flush.from_url(_os_flush.getenv("REDIS_URL", "redis://redis:6379/0"))\n',
        f'{indent}    _rf.flushall()\n',
        f'{indent}except Exception:\n',
        f'{indent}    pass\n',
        f'\n',
    ]

    cleaned[insert_after+1:insert_after+1] = flush_lines

    with open(TARGET, 'w') as f:
        f.writelines(cleaned)

    print(f"Flush block inserted after line {insert_after+1} with indent '{indent}'")
    
    # Verify syntax
    import subprocess
    result = subprocess.run(['python3', '-m', 'py_compile', TARGET], capture_output=True, text=True)
    if result.returncode == 0:
        print("Syntax check: PASS")
    else:
        print(f"Syntax check: FAIL\n{result.stderr}")
