"""Run this to see the actual column names in key tables."""
import sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()
tables = ['narrative_trends', 'analytics_snapshots', 'social_posts',
          'normalised_posts', 'opportunity_alignment_scores',
          'stakeholder_influence_profiles', 'opportunity_assessments']

for table in tables:
    try:
        result = db.execute(text(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)).fetchall()
        if result:
            print(f"\n{table}:")
            for col, dtype in result:
                print(f"  {col} ({dtype})")
        else:
            print(f"\n{table}: NOT FOUND")
    except Exception as e:
        print(f"\n{table}: ERROR - {e}")
db.close()
