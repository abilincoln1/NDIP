path = '/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py'
with open(path) as f:
    lines = f.readlines()

# Find the target line and replace it with a correctly indented block
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == 'return cast(Any, type_)._evaluate(globalns, localns, set())' or \
       stripped == 'return cast(Any, type_)._evaluate(globalns, localns, recursive_guard=frozenset())':
        # Detect the indentation of this line
        indent = len(line) - len(line.lstrip())
        base = ' ' * indent
        inner = ' ' * (indent + 4)
        lines[i] = (
            base + 'try:\n' +
            inner + 'return cast(Any, type_)._evaluate(globalns, localns, recursive_guard=frozenset())\n' +
            base + 'except TypeError:\n' +
            inner + 'return cast(Any, type_)._evaluate(globalns, localns)\n'
        )
        print(f'Patched line {i}')
        print(repr(lines[i]))
        break
else:
    print('Target line not found')
    for i, l in enumerate(lines[60:72], 60):
        print(f'{i}: {repr(l)}')

with open(path, 'w') as f:
    f.writelines(lines)
print('Done')
