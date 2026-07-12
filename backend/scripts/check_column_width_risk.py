"""
Check whether StakeholderRelationship.relationship_type's actual DB
column width can accept the new, longer RelationshipType values
(SAEnum(native_enum=False) widths are typically derived from the enum's
values at the time the table was created -- if the live table's column
is narrower than 14-20 chars, inserting a new long value could fail or
truncate silently).

Run: docker exec agora-backend-1 python scripts/check_column_width_risk.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import engine
from sqlalchemy import inspect as sa_inspect

inspector = sa_inspect(engine)
for table in ["stakeholder_registry", "stakeholder_relationships"]:
    print(f"=== {table} ===")
    for col in inspector.get_columns(table):
        print(f"  {col['name']:25s} {col['type']}")
