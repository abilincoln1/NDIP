"""Show the exact composite_index line in the live materialise file."""
with open('/app/app/services/materialise_intelligence.py', 'r') as f:
    content = f.read()
idx = content.find('composite_index')
while idx != -1:
    print(repr(content[max(0,idx-20):idx+60]))
    idx = content.find('composite_index', idx+1)
