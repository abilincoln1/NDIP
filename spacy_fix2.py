path = '/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py'
with open(path) as f:
    lines = f.readlines()

# Find and show lines 60-72
for i, l in enumerate(lines[60:72], 60):
    print(f'{i}: {repr(l)}')

# Fix lines 65-68 directly
# Line 65 should be: '        try:\n'
# Line 66 should be: '            return cast(Any, type_)._evaluate(globalns, localns, frozenset())\n'
# Line 67 should be: '        except TypeError:\n'
# Line 68 should be: '            return cast(Any, type_)._evaluate(globalns, localns, set())\n'

fixed = False
for i in range(len(lines)):
    if lines[i].strip() == 'try:' and i+1 < len(lines) and 'frozenset' in lines[i+1]:
        # Fix indentation - detect base indent from try: line
        indent = len(lines[i]) - len(lines[i].lstrip())
        base = ' ' * indent
        inner = ' ' * (indent + 4)
        lines[i]   = base + 'try:\n'
        lines[i+1] = inner + 'return cast(Any, type_)._evaluate(globalns, localns, frozenset())\n'
        if i+2 < len(lines) and 'except' in lines[i+2]:
            lines[i+2] = base + 'except TypeError:\n'
        if i+3 < len(lines) and 'set()' in lines[i+3]:
            lines[i+3] = inner + 'return cast(Any, type_)._evaluate(globalns, localns, set())\n'
        fixed = True
        print(f'Fixed block at line {i}')
        break

if fixed:
    with open(path, 'w') as f:
        f.writelines(lines)
    print('Written successfully')
    # Verify
    for i2, l in enumerate(lines[60:72], 60):
        print(f'{i2}: {repr(l)}')
else:
    print('Block not found - showing all lines with try/frozenset:')
    for i, l in enumerate(lines):
        if 'frozenset' in l or ('try:' in l and i > 55 and i < 80):
            print(f'{i}: {repr(l)}')
