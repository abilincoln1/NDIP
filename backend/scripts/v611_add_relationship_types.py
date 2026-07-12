"""
NDIP V6.1.1 Phase C -- Add 5 new RelationshipType values (HOLDS_OFFICE,
LEADS, PART_OF, SUPERVISES, APPOINTS), confirmed to fit the live
VARCHAR(14) relationship_type column. Code-level enum addition only, no
migration required (consistent with V6.2's earlier confirmed finding
that relationship_type is a plain varchar, not a native Postgres enum).

Run: docker exec agora-backend-1 python scripts/v611_add_relationship_types.py
"""
PATH = "/app/app/models/models.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    MONITORS = "MONITORS"'''

new = '''    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    MONITORS = "MONITORS"
    # V6.1.1 additions -- authority graph vocabulary, confirmed to fit VARCHAR(14)
    HOLDS_OFFICE = "HOLDS_OFFICE"
    LEADS = "LEADS"
    PART_OF = "PART_OF"
    SUPERVISES = "SUPERVISES"
    APPOINTS = "APPOINTS"'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully.")
