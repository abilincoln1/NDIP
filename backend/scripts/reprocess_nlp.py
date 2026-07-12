"""
Reprocess all unprocessed NLP posts.
Run after major ingest to ensure all posts have sentiment, entities, topics, narratives.
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.services.normalisation import normalise_unprocessed_batch
from app.analytics.intelligence import process_unprocessed_batch, reprocess_all
from app.models.models import NormalisedPost
from sqlalchemy import func

db = SessionLocal()

# Check current state
total = db.query(func.count(NormalisedPost.id)).scalar() or 0
processed = db.query(func.count(NormalisedPost.id)).filter(
    NormalisedPost.nlp_processed == True
).scalar() or 0
pending = total - processed

print(f"Total normalised posts: {total}")
print(f"NLP processed: {processed}")
print(f"Pending: {pending}")

if pending > 0:
    print(f"\nProcessing {pending} pending posts...")
    count = 0
    batch = 500
    while True:
        n = process_unprocessed_batch(db, batch)
        count += n
        print(f"  Processed batch: {n}")
        if n < batch:
            break
    print(f"Total processed: {count}")
else:
    print("\nAll posts already processed.")
    # Check if we need to reprocess for quality
    print("\nRunning quality reprocess...")
    result = reprocess_all(db)
    print(f"Reprocessed: {result}")

db.close()
print("\nDone")
