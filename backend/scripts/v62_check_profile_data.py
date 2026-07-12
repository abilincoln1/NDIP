"""Check actual data quality in stakeholder_influence_profiles."""
import sys; sys.path.insert(0, '/app')
from sqlalchemy import text
from app.db.database import SessionLocal
db = SessionLocal()

result = db.execute(text("""
    SELECT sip.stakeholder_id, sr.name,
           sip.composite_index, sip.influence_score,
           sip.momentum_score, sip.influence_level,
           sip.computed_at
    FROM stakeholder_influence_profiles sip
    JOIN stakeholder_registry sr ON sr.id = sip.stakeholder_id
    ORDER BY sip.composite_index DESC
    LIMIT 10
"""))
print("Top 10 influence profiles by composite_index:")
for row in result:
    print(f"  {row[1]}: composite={row[2]:.2f}, influence={row[3]:.2f}, momentum={row[4]:.2f}, level={row[5]}, computed={row[6]}")

# Also check for zeros
zeros = db.execute(text(
    "SELECT COUNT(*) FROM stakeholder_influence_profiles WHERE composite_index = 0.0"
)).scalar()
total = db.execute(text("SELECT COUNT(*) FROM stakeholder_influence_profiles")).scalar()
print(f"\nZero composite_index: {zeros}/{total}")
db.close()
