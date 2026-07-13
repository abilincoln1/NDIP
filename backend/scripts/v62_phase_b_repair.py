#!/usr/bin/env python3
"""
NDIP V6.2
Phase B Repair

Repairs the first materialised-read patch by:

1. Removing malformed imports
2. Replacing only the intended read calls
3. Leaving compute endpoints untouched
4. Creating backups before editing
"""

from pathlib import Path
import shutil

ROOT = Path("/app/app/api/routes")

FILES = [
    ROOT / "situation_room.py",
    ROOT / "leadership_pack.py",
    ROOT / "strategic_outcome.py",
]


def backup(path):
    backup_file = path.with_suffix(path.suffix + ".bak_v62_phase_b_repair")
    shutil.copy2(path, backup_file)
    print(f"Backup: {backup_file}")


def repair_situation_room(text):

    text = text.replace(
        "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n",
        ""
    )

    text = text.replace(
        "from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders",
        "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n"
        "        from app.services.stakeholder_influence import get_emerging_stakeholders"
    )

    text = text.replace(
        "_influence_ranked = get_top_influence_stakeholders(",
        "_influence_ranked = get_materialised_top_influence_stakeholders("
    )

    return text


def repair_leadership_pack(text):

    text = text.replace(
        "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n",
        ""
    )

    text = text.replace(
        "from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders",
        "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n"
        "        from app.services.stakeholder_influence import get_emerging_stakeholders"
    )

    text = text.replace(
        "_influence_ranked = get_top_influence_stakeholders(",
        "_influence_ranked = get_materialised_top_influence_stakeholders("
    )

    return text


def repair_strategic_outcome(text):

    text = text.replace(
        "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n",
        ""
    )

    target = (
        '@router.get("/v61/stakeholders/influence/top")'
    )

    idx = text.find(target)

    if idx != -1:

        end = text.find(
            '@router.get("/v61/stakeholders/{stakeholder_id}/influence")',
            idx
        )

        block = text[idx:end]

        block = block.replace(
            "from app.services.stakeholder_influence import get_top_influence_stakeholders",
            "from app.services.materialised_reads import get_materialised_top_influence_stakeholders"
        )

        block = block.replace(
            "get_top_influence_stakeholders(",
            "get_materialised_top_influence_stakeholders("
        )

        text = text[:idx] + block + text[end:]

    return text


def repair_file(path):

    backup(path)

    text = path.read_text(encoding="utf-8")

    if path.name == "situation_room.py":
        text = repair_situation_room(text)

    elif path.name == "leadership_pack.py":
        text = repair_leadership_pack(text)

    elif path.name == "strategic_outcome.py":
        text = repair_strategic_outcome(text)

    path.write_text(text, encoding="utf-8")

    print(f"Patched: {path.name}")


def main():

    print("=" * 70)
    print("NDIP V6.2 PHASE B REPAIR")
    print("=" * 70)

    for f in FILES:
        repair_file(f)

    print()
    print("Repair complete.")
    print("Restart backend.")
    print("=" * 70)


if __name__ == "__main__":
    main()