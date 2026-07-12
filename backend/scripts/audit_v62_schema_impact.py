"""
NDIP V6.2 Pre-Build Audit -- Schema Extension Impact Assessment

Before extending StakeholderRegistry / StakeholderRelationship for V6.2,
this answers the specific questions raised: how much data already
exists, how heavily are these tables used by other code, what are the
current cardinality assumptions, and will existing callers continue to
work if new nullable fields are added.

Run: docker exec agora-backend-1 python scripts/audit_v62_schema_impact.py
"""
import sys
sys.path.insert(0, '/app')
import subprocess

from app.db.database import SessionLocal
from app.models.models import (
    StakeholderRegistry, StakeholderRelationship, StakeholderProfile,
    StakeholderInfluenceProfile, StakeholderMomentumSnapshot,
    OpportunityAssessment, OpportunityAlignmentScore, RecommendationRecord,
    OutcomeChainLink,
)

db = SessionLocal()

print("=" * 70)
print("  SECTION 1 -- DATA VOLUME")
print("=" * 70)
print(f"  StakeholderRegistry rows: {db.query(StakeholderRegistry).count()}")
print(f"  StakeholderRelationship rows: {db.query(StakeholderRelationship).count()}")
print(f"  StakeholderProfile rows (V6.0): {db.query(StakeholderProfile).count()}")
print(f"  StakeholderInfluenceProfile rows (V6.1): {db.query(StakeholderInfluenceProfile).count()}")
print(f"  StakeholderMomentumSnapshot rows (V6.1): {db.query(StakeholderMomentumSnapshot).count()}")
print(f"  OutcomeChainLink rows: {db.query(OutcomeChainLink).count()}")

print()
print("=" * 70)
print("  SECTION 2 -- CURRENT SCHEMA (exact columns, for extension planning)")
print("=" * 70)
print("  StakeholderRegistry columns:")
for c in StakeholderRegistry.__table__.columns:
    print(f"    {c.name:30s} {c.type}  nullable={c.nullable}")
print()
print("  StakeholderRelationship columns:")
for c in StakeholderRelationship.__table__.columns:
    print(f"    {c.name:30s} {c.type}  nullable={c.nullable}")

print()
print("=" * 70)
print("  SECTION 3 -- CATEGORY ENUM USAGE (cardinality check)")
print("=" * 70)
from sqlalchemy import func
category_counts = db.query(StakeholderRegistry.category, func.count(StakeholderRegistry.id)).group_by(StakeholderRegistry.category).all()
for cat, count in category_counts:
    print(f"  {cat}: {count}")

print()
print("=" * 70)
print("  SECTION 4 -- CODE DEPENDENCY SCAN (who actually queries these tables)")
print("=" * 70)
result = subprocess.run(
    ["grep", "-rl", "StakeholderRegistry\\|StakeholderRelationship", "/app/app/"],
    capture_output=True, text=True
)
files = [f for f in result.stdout.strip().split("\n") if f and "__pycache__" not in f]
print(f"  {len(files)} files reference StakeholderRegistry or StakeholderRelationship:")
for f in files:
    print(f"    {f}")

print()
print("=" * 70)
print("  SECTION 5 -- RELATIONSHIP_TYPE ENUM USAGE")
print("=" * 70)
from app.models.models import RelationshipType
rel_counts = db.query(StakeholderRelationship.relationship_type, func.count(StakeholderRelationship.id)).group_by(StakeholderRelationship.relationship_type).all()
for rt, count in rel_counts:
    print(f"  {rt}: {count}")
print(f"\n  Current RelationshipType enum values: {[t.value for t in RelationshipType]}")

db.close()
print()
print("=" * 70)
print("  AUDIT COMPLETE")
print("=" * 70)
