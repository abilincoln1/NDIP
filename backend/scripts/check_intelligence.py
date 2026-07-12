import sys
sys.path.insert(0, '/app')
from app.db.database import SessionLocal
from app.analytics.intelligence import (
    get_sentiment_trends, get_narrative_trends,
    get_source_comparison, get_top_entities
)
db = SessionLocal()
st = get_sentiment_trends(db, 30)
nar = get_narrative_trends(db, 30)
src = get_source_comparison(db, 30)
ent = get_top_entities(db, 30)
print(f"Sentiment trend days: {len(st)}")
print(f"Narratives: {len(nar)}")
print(f"Sources: {len(src)}")
print(f"Entities: {len(ent)}")
if st: print(f"Sample sentiment: {st[0]}")
if nar: print(f"Sample narrative: {nar[0]}")
if src: print(f"Sample source: {src[0]}")
db.close()
print("DONE")
