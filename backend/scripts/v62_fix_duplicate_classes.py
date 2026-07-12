"""
NDIP V6.2 -- Fix duplicate StakeholderEngagement/StakeholderWatchlist
class definitions.

Root cause: the original patch script's class-append step (Patch 6) was
written as an unconditional append, not guarded by the same
anchor-exists check used for the other 5 patches. When the patch script
was run a second time (to pick up the StakeholderType fix), it appended
the same two classes again, producing a duplicate table definition error
in SQLAlchemy.

This script finds the entire V6.2 class block (from the section marker
comment through the end of StakeholderWatchlist) and keeps only the
first occurrence, removing any subsequent duplicates.

Run: docker exec agora-backend-1 python scripts/v62_fix_duplicate_classes.py
"""
PATH = "/app/app/models/models.py"

with open(PATH, "r") as f:
    content = f.read()

marker = "# V6.2 — Stakeholder Intelligence & Engagement System (SIES)"
count = content.count(marker)
print(f"Occurrences of the V6.2 section marker found: {count}")

if count <= 1:
    print("No duplication found (or already fixed) -- no changes made.")
else:
    # Find the start of each full V6.2 block (back up to the preceding
    # "# ===...===" banner line that precedes the marker, so the whole
    # banner+marker+banner+blank-line preamble is captured consistently)
    banner = "# " + "=" * 77
    block_start_token = banner + "\n" + marker

    first_start = content.find(block_start_token)
    second_start = content.find(block_start_token, first_start + len(block_start_token))

    if second_start == -1:
        print("Could not locate a second occurrence using the banner+marker token -- aborting without changes.")
    else:
        # Keep everything up to (not including) the second occurrence's
        # banner -- i.e. truncate the file there, since the V6.2 block
        # (both class definitions) was always appended at the very end of
        # the file with nothing after it.
        # Back up to the start of the banner line for the second occurrence.
        truncate_at = second_start
        kept = content[:truncate_at].rstrip() + "\n"

        with open(PATH, "w") as f:
            f.write(kept)

        # Verify
        with open(PATH, "r") as f:
            verify_content = f.read()
        new_count = verify_content.count(marker)
        print(f"After cleanup, occurrences remaining: {new_count}")
        print("File written.")
