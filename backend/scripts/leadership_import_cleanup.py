from pathlib import Path

path = Path("/app/app/api/routes/leadership_pack.py")

text = path.read_text(encoding="utf-8")

# Add module-level imports after narrative intelligence import
marker = "from app.services.narrative_intelligence import generate_situation_room\n"

if "from app.services.materialised_reads import get_materialised_top_influence_stakeholders" not in text.split("router =")[0]:
    text = text.replace(
        marker,
        marker +
        "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n"
        "from app.services.stakeholder_influence import get_emerging_stakeholders\n"
    )

# Remove local imports only
text = text.replace(
    "        from app.services.materialised_reads import get_materialised_top_influence_stakeholders\n",
    ""
)

text = text.replace(
    "        from app.services.stakeholder_influence import get_emerging_stakeholders\n",
    ""
)

path.write_text(text, encoding="utf-8")

print("leadership_pack.py import cleanup complete")