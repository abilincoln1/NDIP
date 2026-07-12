"""
NewsAPI connector — 80,000+ global news sources.
Free tier: 100 requests/day, 30-day article history.
Get key at: https://newsapi.org
"""
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector, RawPost
from app.core.config import get_settings

settings = get_settings()
NEWSAPI_BASE = "https://newsapi.org/v2"


class NewsConnector(BaseConnector):
    platform = "newsapi"

    @property
    def is_configured(self) -> bool:
        return bool(getattr(settings, 'news_api_key', ''))

    async def fetch(self, query: str, max_results: int = 100) -> list[RawPost]:
        if not self.is_configured:
            return []

        posts = []
        async with httpx.AsyncClient(timeout=20) as client:
            try:
                resp = await client.get(
                    f"{NEWSAPI_BASE}/everything",
                    params={
                        "q": query,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": min(max_results, 100),
                        "apiKey": settings.news_api_key,
                    }
                )
                resp.raise_for_status()
                articles = resp.json().get("articles", [])

                for article in articles:
                    text = f"{article.get('title','')} {article.get('description','')} {article.get('content','')[:500]}".strip()
                    if not text or text == "  ":
                        continue
                    pub_date = article.get("publishedAt")
                    pub_dt: Optional[datetime] = None
                    if pub_date:
                        try:
                            pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        except ValueError:
                            pass
                    posts.append(RawPost(
                        platform=self.platform,
                        external_id=article.get("url", "")[:200],
                        content_text=text[:2000],
                        url=article.get("url"),
                        language="en",
                        published_at=pub_dt,
                        query_tag=query,
                    ))
            except Exception as e:
                print(f"[NewsConnector] error: {e}")

        return posts
