"""Check the real text around get_top_influence_stakeholders."""
with open('/app/app/services/stakeholder_influence.py', 'r') as f:
    content = f.read()
idx = content.find('def get_top_influence_stakeholders')
print(repr(content[idx:idx+600]))
