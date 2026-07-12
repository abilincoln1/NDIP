#!/usr/bin/env python3
import sys, os, random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal, engine, Base
from app.models.models import (
    AdminUser, Participant, Event, EventAttendance,
    Engagement, EngagementType, SentimentRecord, SentimentLabel,
    Topic, SocialPost, SocialPlatform, AnalyticsSnapshot,
)
import hashlib
# Use passlib directly with a short password
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def utcnow():
    return datetime.now(timezone.utc)

def days_ago(d):
    return utcnow() - timedelta(days=d)

print("Seeding admin user...")
# Keep password short — bcrypt limit is 72 bytes
ADMIN_PASSWORD = "Agora2024"
if not db.query(AdminUser).filter(AdminUser.email == "admin@agora.rtifn.org").first():
    db.add(AdminUser(
        email="admin@agora.rtifn.org",
        hashed_password=pwd_context.hash(ADMIN_PASSWORD),
        full_name="Agora Administrator",
    ))
    db.commit()

print("Seeding participants...")
COUNTRIES = ["Nigeria","United Kingdom","United States","Ghana","Kenya",
             "Canada","South Africa","Germany","France","Australia"]
PROFESSIONS = ["Engineer","Doctor","Lawyer","Educator","Entrepreneur",
               "Researcher","Designer","Journalist","Consultant","Student"]

for i in range(120):
    email_hash = hashlib.sha256(f"user{i}@example.com".encode()).hexdigest()
    if not db.query(Participant).filter(Participant.email_hash == email_hash).first():
        db.add(Participant(
            email_hash=email_hash,
            country=random.choice(COUNTRIES),
            city=f"City {i % 20}",
            profession=random.choice(PROFESSIONS),
            skills=",".join(random.sample(["Python","Leadership","Design","Research","Community","Policy"],3)),
            interests=random.choice(["Civic Tech","Education","Health","Policy"]),
            consent_given=True,
            created_at=days_ago(random.randint(0, 180)),
        ))
db.commit()

print("Seeding events...")
all_participants = db.query(Participant).all()
EVENT_TYPES = ["Webinar","Workshop","Summit","Networking","Conference"]
for i in range(15):
    db.add(Event(
        title=f"Diaspora {EVENT_TYPES[i % len(EVENT_TYPES)]} {i+1}",
        description="A community engagement event.",
        event_type=EVENT_TYPES[i % len(EVENT_TYPES)],
        country=random.choice(COUNTRIES),
        city=f"City {i}",
        starts_at=days_ago(random.randint(-30, 120)),
        capacity=random.randint(50, 500),
        is_online=random.choice([True, False]),
    ))
db.commit()

print("Seeding engagements...")
for _ in range(600):
    db.add(Engagement(
        participant_id=random.choice(all_participants).id if random.random() > 0.2 else None,
        engagement_type=random.choice(list(EngagementType)),
        source=random.choice(["newsletter","website","event","social"]),
        created_at=days_ago(random.randint(0, 90)),
    ))
db.commit()

print("Seeding social posts + sentiment...")
PLATFORMS = list(SocialPlatform)
TEXTS = [
    "The diaspora community is making incredible strides in policy advocacy.",
    "Disappointed by the lack of representation in recent discussions.",
    "Another great webinar from the network. Feeling inspired!",
    "We need more transparency in how diaspora funds are allocated.",
    "Proud to see our community leaders recognised on the world stage.",
    "Amazing turnout at the community summit this weekend!",
]
for _ in range(300):
    post = SocialPost(
        platform=random.choice(PLATFORMS),
        external_id=f"seed_{random.randint(100000,999999)}",
        content_text=random.choice(TEXTS),
        language="en",
        published_at=days_ago(random.randint(0, 30)),
        query_tag="diaspora community",
    )
    db.add(post)
    db.flush()
    score = random.uniform(-0.8, 0.8)
    label = SentimentLabel.positive if score > 0.1 else (SentimentLabel.negative if score < -0.1 else SentimentLabel.neutral)
    db.add(SentimentRecord(post_id=post.id, label=label, score=round(score,4), created_at=post.published_at))
db.commit()

print("Seeding topics...")
TOPIC_NAMES = ["diaspora","community","policy","education","health","advocacy","representation","leadership"]
for name in TOPIC_NAMES:
    for day_offset in range(14):
        db.add(Topic(
            name=name,
            platform=random.choice(PLATFORMS),
            mention_count=random.randint(5, 200),
            date_bucket=days_ago(day_offset).replace(hour=0,minute=0,second=0,microsecond=0),
            momentum_score=round(random.uniform(-0.5, 0.5), 4),
        ))
db.commit()

print("Seeding analytics snapshots...")
for day_offset in range(60):
    db.add(AnalyticsSnapshot(
        snapshot_date=days_ago(day_offset),
        engagement_index=round(random.uniform(0.3, 2.5), 4),
        participation_index=round(random.uniform(0.1, 0.8), 4),
        growth_rate=round(random.uniform(-0.05, 0.15), 4),
        sentiment_score=round(random.uniform(-0.3, 0.6), 4),
        topic_momentum_score=round(random.uniform(0.0, 0.8), 4),
        total_participants=random.randint(80, 150),
        total_engagements=random.randint(200, 800),
        new_participants=random.randint(2, 12),
    ))
db.commit()
db.close()

print("\n✓ Seed complete.")
print("  Login: admin@agora.rtifn.org / Agora2024")
