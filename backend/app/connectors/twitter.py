"""
X (Twitter) API v2 connector — Recent Search endpoint.
Uses Bearer Token (app-only auth). No author data stored.
Requires: TWITTER_BEARER_TOKEN env var.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector, RawPost
from app.core.config import get_settings

settings = get_settings()

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class TwitterConnector(BaseConnector):
    platform = "twitter"

    @property
    def is_configured(self) -> bool:
        return bool(settings.twitter_bearer_token)

    async def fetch(self, query: str, max_results: int = 100) -> list[RawPost]:
        if not self.is_configured:
            return []

        try:
            headers = {"Authorization": f"Bearer {settings.twitter_bearer_token}"}
            params = {
                "query": f"{query} -is:retweet lang:en",
                "max_results": min(max(max_results, 10), 100),
                "tweet.fields": "created_at,lang,text",
                # Deliberately exclude author_id / user fields
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(TWITTER_SEARCH_URL, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                posts = []
                for tweet in data.get("data", []):
                    pub_dt: Optional[datetime] = None
                    created = tweet.get("created_at", "")
                    if created:
                        try:
                            pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    posts.append(RawPost(
                        platform=self.platform,
                        external_id=tweet["id"],
                        content_text=tweet.get("text", "")[:1000],
                        url=None,  # No permalink without author handle
                        language=tweet.get("lang"),
                        published_at=pub_dt,
                        query_tag=query,
                    ))

                return posts

        except (httpx.HTTPError, Exception) as e:
            print(f"[TwitterConnector] fetch failed: {e}")
            return []
