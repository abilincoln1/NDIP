"""
Patch activities_v3.py to include project_id in ActivityCreate schema and INSERT.
Run: docker exec ndip-backend-1 python3 /tmp/patch_s5_activity_project.py
"""
import subprocess

TARGET = '/app/app/api/routes/activities_v3.py'

with open(TARGET, 'r') as f:
    c = f.read()

# Add project_id to ActivityCreate schema
c = c.replace(
    'class ActivityCreate(BaseModel):\n    activity_type: str',
    'class ActivityCreate(BaseModel):\n    project_id: Optional[str] = None\n    activity_type: str'
)

# Add project_id to INSERT columns
c = c.replace(
    '            gps_lat, gps_lng, location_text,\n            verification_status, created_at, updated_at\n        ) VALUES (',
    '            gps_lat, gps_lng, location_text,\n            project_id,\n            verification_status, created_at, updated_at\n        ) VALUES ('
)

# Add project_id to INSERT values
c = c.replace(
    '            :gps_lat, :gps_lng, :location_text,\n            \'Draft\', now(), now()',
    '            :gps_lat, :gps_lng, :location_text,\n            :project_id,\n            \'Draft\', now(), now()'
)

# Add project_id to params dict
c = c.replace(
    '        "location_text": payload.location_text,\n    })',
    '        "location_text": payload.location_text,\n        "project_id": payload.project_id,\n    })'
)

with open(TARGET, 'w') as f:
    f.write(c)

r = subprocess.run(['python3', '-m', 'py_compile', TARGET], capture_output=True, text=True)
print(f'Syntax: {"PASS" if r.returncode == 0 else r.stderr}')
print(f'project_id in schema: {"project_id: Optional" in c}')
print(f'project_id in INSERT cols: {"project_id," in c}')
print(f'project_id in params: {"project_id\": payload" in c}')
print('Done. Watchfiles will auto-reload.')
