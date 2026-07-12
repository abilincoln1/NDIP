path = '/usr/local/lib/python3.12/site-packages/pydantic/v1/typing.py'
with open(path) as f:
    lines = f.readlines()

# Show current state around the problem
print("BEFORE:")
for i, l in enumerate(lines[60:75], 60):
    print(f'{i}: {repr(l)}')

# Find the evaluate_forwardref function and replace lines 65 onwards
# until we hit a blank line or next function
# Strategy: find line 65 (try:) and rebuild from scratch

# Remove all lines from 65 to first blank line after the try block
start = None
for i, l in enumerate(lines):
    if i > 60 and l.strip() == 'try:':
        start = i
        break

if start is None:
    print("Could not find try: block")
else:
    # Find end of the broken block
    end = start
    for i in range(start, min(start+10, len(lines))):
        if 'set()' in lines[i] or 'frozenset()' in lines[i]:
            end = i
    
    print(f"Replacing lines {start} to {end+1}")
    
    # Replace with correct 4-line block
    correct = [
        '        try:\n',
        '            return cast(Any, type_)._evaluate(globalns, localns, frozenset())\n',
        '        except TypeError:\n',
        '            return cast(Any, type_)._evaluate(globalns, localns, set())\n',
    ]
    
    lines = lines[:start] + correct + lines[end+1:]
    
    with open(path, 'w') as f:
        f.writelines(lines)
    
    print("\nAFTER:")
    for i, l in enumerate(lines[60:75], 60):
        print(f'{i}: {repr(l)}')
    print("Done")
