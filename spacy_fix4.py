path = '/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py'
with open(path) as f:
    lines = f.readlines()

# Find and replace lines 65-68 with the correct keyword argument call
start = None
for i, l in enumerate(lines):
    if i > 60 and l.strip() == 'try:':
        start = i
        break

if start is not None:
    end = start
    for i in range(start, min(start+8, len(lines))):
        if 'set()' in lines[i] or 'frozenset()' in lines[i]:
            end = i

    # Use recursive_guard=frozenset() keyword argument - correct for Python 3.12
    correct = [
        '        try:\n',
        '            return cast(Any, type_)._evaluate(globalns, localns, recursive_guard=frozenset())\n',
        '        except TypeError:\n',
        '            return cast(Any, type_)._evaluate(globalns, localns)\n',
    ]

    lines = lines[:start] + correct + lines[end+1:]

    with open(path, 'w') as f:
        f.writelines(lines)

    print("Fixed. Lines 65-68 now:")
    for i, l in enumerate(lines[63:70], 63):
        print(f'{i}: {repr(l)}')
else:
    print("try: block not found")
