"""
NDIP V6.2 -- Fix duplicate RelationshipType enum values.

The "RelationshipType new values" patch ran twice across two separate
patch-script executions (the first run succeeded; a second run's anchor
guard should have prevented a re-match, but the anchor text used in that
patch was unaffected by the StakeholderType blank-line fix and matched
again because the original 5-value block it searches for still existed
unchanged each time -- enum classes don't get modified by replacing
their own un-altered prefix). Result: the 8 new RelationshipType values
are duplicated in the live file. Python silently allows duplicate enum
member names (the second definition wins), so this did not crash
anything, but it is genuine duplicated/dead code that must be cleaned up.

This script finds the RelationshipType class block and removes the
duplicate set of 8 new values, keeping exactly one copy of each.

Run: docker exec agora-backend-1 python scripts/v62_fix_duplicate_enum.py
"""
PATH = "/app/app/models/models.py"

with open(PATH, "r") as f:
    content = f.read()

duplicated_block = '''    # V6.2 additions -- all confirmed to fit the live VARCHAR(14) column
    APPROVES = "APPROVES"
    INFLUENCES = "INFLUENCES"
    IMPLEMENTS = "IMPLEMENTS"
    OVERSEES = "OVERSEES"
    CONNECTS_TO = "CONNECTS_TO"
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    MONITORS = "MONITORS"
'''

count = content.count(duplicated_block)
print(f"Occurrences of the V6.2 RelationshipType additions block found: {count}")

if count <= 1:
    print("No duplication found (or already fixed) -- no changes made.")
else:
    # Keep the first occurrence, remove all subsequent ones.
    first_idx = content.find(duplicated_block)
    after_first = first_idx + len(duplicated_block)
    before = content[:after_first]
    rest = content[after_first:]
    rest_cleaned = rest.replace(duplicated_block, "")
    content = before + rest_cleaned

    new_count = content.count(duplicated_block)
    print(f"After cleanup, occurrences remaining: {new_count}")

    with open(PATH, "w") as f:
        f.write(content)
    print("File written.")
