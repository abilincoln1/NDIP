path = '/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py'
with open(path) as f:
    c = f.read()

# Check current state around line 66
lines = c.split('\n')
for i, l in enumerate(lines[60:72], 60):
    print(f'{i}: {repr(l)}')

old = 'return cast(Any, type_)._evaluate(globalns, localns, set())'
new = 'try:\n        return cast(Any, type_)._evaluate(globalns, localns, frozenset())\n    except TypeError:\n        return cast(Any, type_)._evaluate(globalns, localns, set())'

if old in c:
    c = c.replace(old, new)
    with open(path, 'w') as f:
        f.write(c)
    print('patched OK')
elif 'frozenset' in c and 'try:' in c:
    print('already patched correctly')
else:
    print('pattern not found - manual inspection needed')
