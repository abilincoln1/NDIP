"""
NDIP V6.2 -- Fix duplicate StakeholderEngagement/StakeholderWatchlist
class definitions, attempt 2.

Root cause of attempt 1's failure: the banner line uses Unicode
box-drawing characters (=), not plain ASCII equals signs, which did not
match the previous fix script's literal "=" * 77 construction.

This version locates the second occurrence by line number (confirmed
live: second marker at line 1044, file is 1115 lines total) and removes
everything from that occurrence's banner start through end of file --
keeping the first, complete copy of the V6.2 classes (lines 966-1043)
intact, including line 965's preceding content.

Run: docker exec agora-backend-1 python scripts/v62_fix_duplicate_classes_v2.py
"""
PATH = "/app/app/models/models.py"

with open(PATH, "r") as f:
    lines = f.readlines()

print(f"Total lines in file: {len(lines)}")

marker = "V6.2 — Stakeholder Intelligence & Engagement System (SIES)"
marker_line_indices = [i for i, line in enumerate(lines) if marker in line]
print(f"Marker found on lines (0-indexed): {marker_line_indices}")
print(f"Marker found on lines (1-indexed, matching file line numbers): {[i+1 for i in marker_line_indices]}")

if len(marker_line_indices) != 2:
    print(f"Expected exactly 2 occurrences, found {len(marker_line_indices)} -- aborting without changes.")
else:
    first_idx, second_idx = marker_line_indices
    # The banner is 3 lines: "# ===...", "# V6.2 ...", "# ===...", and it
    # starts one line above the marker line itself.
    second_banner_start = second_idx - 1  # 0-indexed line just before the marker = the opening "# ===" line

    # Sanity check: confirm that line actually looks like a banner line
    # before truncating, rather than assuming the offset is correct.
    banner_candidate = lines[second_banner_start].strip()
    print(f"Line immediately before second marker (should be a banner '# ===' line): {banner_candidate!r}")

    if not banner_candidate.startswith("#") or "=" not in banner_candidate and "═" not in banner_candidate:
        print("Line before second marker does not look like a banner -- aborting without changes for safety.")
    else:
        kept_lines = lines[:second_banner_start]
        # Trim any trailing blank lines, then ensure exactly one trailing newline.
        while kept_lines and kept_lines[-1].strip() == "":
            kept_lines.pop()
        kept_content = "".join(kept_lines).rstrip() + "\n"

        with open(PATH, "w") as f:
            f.write(kept_content)

        with open(PATH, "r") as f:
            verify_lines = f.readlines()
        verify_count = sum(1 for line in verify_lines if marker in line)
        print(f"\nFile truncated. New total lines: {len(verify_lines)}")
        print(f"Marker occurrences remaining: {verify_count}")
