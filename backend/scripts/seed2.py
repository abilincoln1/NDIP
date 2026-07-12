import sys, os, random, hashlib
from datetime import datetime, timedelta, timezone
sys.path.insert(0, '/app')
os.chdir('/app')
from dotenv import load_dotenv
load_dotenv()
from app.db.database import SessionLocal, engine, Base
from app.models.models import AdminUser, Participant, Engagement, EngagementType, AnalyticsSnapshot
Base.metadata.create_all(bind=engine)
db = SessionLocal()
now = datetime.now(timezone.utc)
def ago(d): return now - timedelta(days=d)
COUNTRIES=["Nigeria","UK","USA","Ghana","Kenya","Canada","South Africa","Germany","France","Australia"]
JOBS=["Engineer","Doctor","Lawyer","Educator","Entrepreneur","Researcher","Designer"]
H="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36zLKCru6VevDjBrJKSRqTe"
if not db.query(AdminUser).filter(AdminUser.email=="admin@agora.rtifn.org").first():
    db.add(AdminUser(email="admin@agora.rtifn.org",hashed_password=H,full_name="Administrator"))
    db.commit()
    print("Admin created")
for i in range(120):
    eh=hashlib.sha256(f"u{i}@x.com".encode()).hexdigest()
    if not db.query(Participant).filter(Participant.email_hash==eh).first():
        db.add(Participant(email_hash=eh,country=random.choice(COUNTRIES),profession=random.choice(JOBS),consent_given=True,created_at=ago(random.randint(0,180))))
db.commit()
print("Participants done")
for _ in range(400):
    db.add(Engagement(engagement_type=random.choice(list(EngagementType)),source="seed",created_at=ago(random.randint(0,90))))
db.commit()
print("Engagements done")
for d in range(60):
    db.add(AnalyticsSnapshot(snapshot_date=ago(d),engagement_index=round(random.uniform(0.3,2.5),4),participation_index=round(random.uniform(0.1,0.8),4),growth_rate=round(random.uniform(-0.05,0.15),4),sentiment_score=round(random.uniform(-0.3,0.6),4),topic_momentum_score=round(random.uniform(0,0.8),4),total_participants=random.randint(80,150),total_engagements=random.randint(200,800),new_participants=random.randint(2,12)))
db.commit()
print("Snapshots done")
db.close()
print("SEED COMPLETE")
print("Login: admin@agora.rtifn.org / Agora2024")
