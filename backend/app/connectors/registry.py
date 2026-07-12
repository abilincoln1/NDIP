"""
Connector registry v2 — orchestrates all connectors with health logging.
Supports: YouTube, Twitter, Reddit, NewsAPI, GDELT, Meta, Nigeria/RSS outlets.
"""
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.connectors.base import RawPost
from app.connectors.youtube import YouTubeConnector
from app.connectors.twitter import TwitterConnector
from app.connectors.reddit import RedditConnector
from app.connectors.news import NewsConnector
from app.connectors.gdelt import GDELTConnector
from app.connectors.meta import MetaConnector
from app.connectors.nigeria import NIGERIA_CONNECTORS, get_nigeria_connector_status
from app.models.models import SocialPost, SocialPlatform, ConnectorHealthLog, IngestionJob
from app.analytics.nlp import analyse_and_store, extract_topics, store_topics

# Core connectors
CORE_CONNECTORS = [
    YouTubeConnector(),
    TwitterConnector(),
    RedditConnector(),
    NewsConnector(),
    GDELTConnector(),
    MetaConnector(),
]

ALL_CONNECTORS = CORE_CONNECTORS + NIGERIA_CONNECTORS


def get_connector_status() -> list[dict]:
    status = []
    for c in CORE_CONNECTORS:
        status.append({"platform": c.platform, "configured": c.is_configured, "type": "api"})
    status.extend(get_nigeria_connector_status())
    return status


def _get_or_create_platform(platform_str: str) -> str:
    """Return platform string — handles both enum and custom RSS platforms."""
    try:
        return SocialPlatform(platform_str).value
    except ValueError:
        return platform_str


def _persist_post(db: Session, raw: RawPost) -> SocialPost | None:
    try:
        # For standard platforms use enum, for RSS use string stored in query_tag
        try:
            platform_enum = SocialPlatform(raw.platform)
        except ValueError:
            platform_enum = SocialPlatform.news  # fallback for RSS connectors

        # Use platform name in query_tag to preserve source identity for RSS feeds
        stored_query_tag = f"{raw.platform}:{raw.query_tag}" if raw.platform not in [p.value for p in SocialPlatform] else raw.query_tag

        existing = db.query(SocialPost).filter(
            SocialPost.external_id == raw.external_id,
            SocialPost.query_tag == stored_query_tag,
        ).first()
        if existing:
            return None

        post = SocialPost(
            platform=platform_enum,
            external_id=raw.external_id[:200],
            content_text=raw.content_text,
            url=raw.url,
            language=raw.language,
            published_at=raw.published_at,
            query_tag=stored_query_tag,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    except IntegrityError:
        db.rollback()
        return None
    except Exception as e:
        db.rollback()
        print(f"[Registry] persist error: {e}")
        return None


def _log_health(db: Session, platform: str, status: str, fetched: int,
                new: int, error: str | None, duration_ms: int):
    db.add(ConnectorHealthLog(
        platform=platform,
        status=status,
        records_fetched=fetched,
        records_new=new,
        error_message=error,
        duration_ms=duration_ms,
    ))
    db.commit()


async def run_ingest(
    db: Session,
    query: str,
    platforms: list[str] | None = None,
    include_nigeria: bool = True,
    triggered_by: str = "manual",
) -> dict:
    """Run all configured connectors. Returns detailed summary."""

    job = IngestionJob(
        query=query,
        platforms=",".join(platforms) if platforms else "all",
        status="running",
        triggered_by=triggered_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    summary = {"query": query, "job_id": job.id, "platforms": {}}
    all_texts = []
    total_fetched = 0
    total_new = 0

    connectors_to_run = ALL_CONNECTORS if include_nigeria else CORE_CONNECTORS

    for connector in connectors_to_run:
        if platforms and connector.platform not in platforms:
            continue
        if not connector.is_configured:
            summary["platforms"][connector.platform] = {
                "status": "not_configured", "fetched": 0, "new": 0
            }
            _log_health(db, connector.platform, "unconfigured", 0, 0, None, 0)
            continue

        start = time.time()
        try:
            raw_posts = await connector.fetch(query, max_results=100)
            saved = 0
            for raw in raw_posts:
                post = _persist_post(db, raw)
                if post:
                    analyse_and_store(db, post)
                    if post.content_text:
                        all_texts.append(post.content_text)
                    saved += 1

            duration = int((time.time() - start) * 1000)
            summary["platforms"][connector.platform] = {
                "status": "ok", "fetched": len(raw_posts), "new": saved
            }
            _log_health(db, connector.platform, "ok", len(raw_posts), saved, None, duration)
            total_fetched += len(raw_posts)
            total_new += saved

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            error_msg = str(e)[:500]
            summary["platforms"][connector.platform] = {
                "status": "error", "error": error_msg
            }
            _log_health(db, connector.platform, "error", 0, 0, error_msg, duration)

    # Update topics
    if all_texts:
        topics = extract_topics(all_texts, top_n=30)
        store_topics(db, topics)

    # Trigger normalisation + NLP pipeline
    from app.services.normalisation import normalise_unprocessed_batch
    from app.analytics.intelligence import process_unprocessed_batch
    normalised = normalise_unprocessed_batch(db, limit=500)
    processed = process_unprocessed_batch(db, limit=200)
    summary["pipeline"] = {"normalised": normalised, "nlp_processed": processed}

    # Complete job
    job.status = "completed"
    job.total_fetched = total_fetched
    job.total_new = total_new
    job.total_normalised = normalised
    job.completed_at = datetime.now(timezone.utc)
    db.commit()

    return summary


def get_recent_health(db: Session, hours: int = 24) -> list[dict]:
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    logs = db.query(ConnectorHealthLog).filter(
        ConnectorHealthLog.checked_at >= since
    ).order_by(ConnectorHealthLog.checked_at.desc()).limit(200).all()

    by_platform: dict = {}
    for log in logs:
        if log.platform not in by_platform:
            by_platform[log.platform] = {
                "platform": log.platform,
                "last_status": log.status,
                "last_checked": log.checked_at.isoformat(),
                "total_fetched": 0,
                "total_new": 0,
                "errors": 0,
                "checks": 0,
            }
        p = by_platform[log.platform]
        p["total_fetched"] += log.records_fetched
        p["total_new"] += log.records_new
        p["checks"] += 1
        if log.status == "error":
            p["errors"] += 1

    return list(by_platform.values())
