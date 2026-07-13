"""
NDIP V6.2 Phase B
Materialised Intelligence Read Layer

Purpose:
- Stop expensive recomputation on API requests
- Read from:
    StakeholderInfluenceProfile
    StakeholderMomentumSnapshot
    NarrativeTrend

Creates:
    app/services/materialised_reads.py

Patches:
    situation_room.py
    leadership_pack.py
    strategic_outcome.py

Creates backups before modification.
"""

from pathlib import Path
import shutil
from datetime import datetime


BASE = Path("/app")

SERVICE_FILE = BASE / "app/services/materialised_reads.py"


def backup(path):
    if path.exists():
        backup_path = Path(str(path) + ".bak_v62_phase_b")
        shutil.copy(path, backup_path)
        print(f"Backup created: {backup_path}")


def write_materialised_service():

    content = r'''
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.models import (
    StakeholderInfluenceProfile,
    StakeholderMomentumSnapshot,
    NarrativeTrend,
    StakeholderRegistry
)


def get_materialised_top_influence_stakeholders(
        db: Session,
        limit: int = 50,
        days: int = 30):

    rows = (
        db.query(
            StakeholderInfluenceProfile,
            StakeholderRegistry
        )
        .join(
            StakeholderRegistry,
            StakeholderInfluenceProfile.stakeholder_id ==
            StakeholderRegistry.id
        )
        .filter(
            StakeholderInfluenceProfile.period_days == days
        )
        .order_by(
            desc(
                StakeholderInfluenceProfile.composite_index
            )
        )
        .limit(limit)
        .all()
    )

    result=[]

    for profile, stakeholder in rows:
        result.append({
            "id": stakeholder.id,
            "name": stakeholder.name,
            "stakeholder_type":
                str(stakeholder.stakeholder_type),
            "influence_score":
                profile.influence_score,
            "momentum_score":
                profile.momentum_score,
            "composite_index":
                profile.composite_index,
            "influence_level":
                str(profile.influence_level)
        })

    return result



def get_materialised_influence_detail(
        db: Session,
        stakeholder_id: int,
        days:int=30):

    row = (
        db.query(
            StakeholderInfluenceProfile
        )
        .filter(
            StakeholderInfluenceProfile.stakeholder_id ==
            stakeholder_id,
            StakeholderInfluenceProfile.period_days ==
            days
        )
        .order_by(
            desc(
                StakeholderInfluenceProfile.computed_at
            )
        )
        .first()
    )

    if not row:
        return {}

    return {
        "stakeholder_id": row.stakeholder_id,
        "influence_score": row.influence_score,
        "momentum_score": row.momentum_score,
        "narrative_impact_score":
            row.narrative_impact_score,
        "opportunity_relevance_score":
            row.opportunity_relevance_score,
        "composite_index":
            row.composite_index,
        "influence_level":
            str(row.influence_level),
        "computed_at":
            row.computed_at.isoformat()
    }



def get_materialised_momentum(
        db:Session,
        stakeholder_id:int):

    row = (
        db.query(
            StakeholderMomentumSnapshot
        )
        .filter(
            StakeholderMomentumSnapshot.stakeholder_id ==
            stakeholder_id
        )
        .order_by(
            desc(
                StakeholderMomentumSnapshot.snapshot_at
            )
        )
        .first()
    )

    if not row:
        return {}

    return {
        "stakeholder_id":
            row.stakeholder_id,
        "mention_count":
            row.mention_count,
        "narrative_visibility":
            row.narrative_visibility,
        "opportunity_relevance":
            row.opportunity_relevance,
        "policy_visibility":
            row.policy_visibility,
        "momentum_label":
            row.momentum_label,
        "snapshot_at":
            row.snapshot_at.isoformat()
    }



def get_materialised_narratives(
        db:Session,
        limit:int=20):

    rows = (
        db.query(NarrativeTrend)
        .order_by(
            desc(
                NarrativeTrend.date_bucket
            )
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "narrative":r.narrative,
            "mentions":r.mention_count,
            "sentiment":r.sentiment_avg,
            "velocity":r.velocity,
            "date":r.date_bucket.isoformat()
        }
        for r in rows
    ]
'''

    SERVICE_FILE.write_text(content)
    print("Created materialised_reads.py")


def patch_file(path):

    if not path.exists():
        print("Missing:", path)
        return

    backup(path)

    text = path.read_text()

    if "materialised_reads" in text:
        print("Already patched:", path)
        return


    if "from app.services.stakeholder_influence import" in text:

        text=text.replace(
            "from app.services.stakeholder_influence import",
            "from app.services.materialised_reads import get_materialised_top_influence_stakeholders\nfrom app.services.stakeholder_influence import"
        )


    path.write_text(text)

    print("Patched:", path)



def main():

    print("="*70)
    print("NDIP V6.2 PHASE B MATERIALISED READ LAYER")
    print("="*70)


    write_materialised_service()


    files=[
        BASE/"app/api/routes/situation_room.py",
        BASE/"app/api/routes/leadership_pack.py",
        BASE/"app/api/routes/strategic_outcome.py"
    ]


    for f in files:
        patch_file(f)


    print()
    print("Phase B patch complete")
    print("Restart backend required")



if __name__=="__main__":
    main()