
# NDIP V8 spaCy/pydantic v1 compatibility patch
import typing as _typing
_orig = _typing.ForwardRef._evaluate
def _patched(self, globalns, localns, *args, **kwargs):
    kwargs.pop('recursive_guard', None)
    for call in [
        lambda: _orig(self, globalns, localns, frozenset()),
        lambda: _orig(self, globalns, localns, set()),
        lambda: _orig(self, globalns, localns),
    ]:
        try: return call()
        except TypeError: continue
    raise TypeError('ForwardRef._evaluate failed')
_typing.ForwardRef._evaluate = _patched
del _typing, _orig, _patched
# End spaCy patch
"""
Normalisation Layer
Transforms raw SocialPost records into NormalisedPost (unified schema).
Stores raw and processed data separately.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.models import SocialPost, NormalisedPost


def normalise_post(db: Session, raw: SocialPost) -> NormalisedPost | None:
    """Convert a raw SocialPost into a NormalisedPost."""
    # Check if already normalised
    existing = db.query(NormalisedPost).filter(
        NormalisedPost.source_platform == str(raw.platform.value),
        NormalisedPost.external_id == raw.external_id,
    ).first()
    if existing:
        return existing

    # Extract actual source platform from query_tag (e.g. "punch_nigeria:query")
    platform_name = str(raw.platform.value)
    if raw.query_tag and ":" in raw.query_tag:
        prefix = raw.query_tag.split(":")[0]
        if prefix and len(prefix) > 2 and prefix != "http":
            platform_name = prefix

    norm = NormalisedPost(
        source_platform=platform_name,
        source_post_id=raw.id,
        external_id=raw.external_id,
        text=raw.content_text,
        language=raw.language or "en",
        url=raw.url,
        published_at=raw.published_at,
        query_tag=raw.query_tag,
        nlp_processed=False,
    )

    db.add(norm)
    try:
        db.commit()
        db.refresh(norm)
        return norm
    except IntegrityError:
        db.rollback()
        return None


def normalise_unprocessed_batch(db: Session, limit: int = 500) -> int:
    """Find raw posts not yet in normalised_posts and normalise them."""
    normalised_ids = db.query(NormalisedPost.source_post_id).filter(
        NormalisedPost.source_post_id.isnot(None)
    ).subquery()

    raw_posts = db.query(SocialPost).filter(
        SocialPost.id.notin_(normalised_ids),
        SocialPost.content_text.isnot(None),
    ).limit(limit).all()

    count = 0
    for raw in raw_posts:
        result = normalise_post(db, raw)
        if result:
            count += 1

    return count


def get_normalisation_stats(db: Session) -> dict:
    from sqlalchemy import func
    total_raw = db.query(func.count(SocialPost.id)).scalar() or 0
    total_norm = db.query(func.count(NormalisedPost.id)).scalar() or 0
    total_nlp = db.query(func.count(NormalisedPost.id)).filter(
        NormalisedPost.nlp_processed == True
    ).scalar() or 0

    return {
        "total_raw": total_raw,
        "total_normalised": total_norm,
        "total_nlp_processed": total_nlp,
        "normalisation_rate": round(total_norm / max(total_raw, 1) * 100, 1),
        "nlp_rate": round(total_nlp / max(total_norm, 1) * 100, 1),
    }
