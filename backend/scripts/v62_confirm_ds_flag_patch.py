"""
Confirm whether the _cached=True flag patch actually applied to the live
file.

Run: docker exec agora-backend-1 python scripts/v62_confirm_ds_flag_patch.py
"""
with open('/app/app/api/routes/national_pulse.py', 'r') as f:
    content = f.read()

idx = content.find('cache_key("decision-support"')
if idx == -1:
    print("Marker not found.")
else:
    print(repr(content[idx:idx+250]))
