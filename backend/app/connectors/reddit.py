"""
Reddit connector using OAuth2 client credentials flow.
Requires: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars.
Create a "script" app at https://www.reddit.com/prefs/apps
"""
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector, RawPost
from app.core.config import get_settings

settings = get_settings()

SUBREDDITS = [
    "Nigeria", "africa", "Nigerian", "diaspora",
    "naija", "AfricanDiaspora", "NigerianDiaspora"
]


class RedditConnector(BaseConnector):
    platform = "reddit"
    _token: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(
            getattr(settings, 'reddit_client_id', '') and
            getattr(settings, 'reddit_client_secret', '')
        )

    async def _get_token(self) -> Optional[str]:
        """Get OAuth2 token using client credentials."""
        if self._token:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    data={"grant_type": "client_credentials"},
                    auth=(settings.reddit_client_id, settings.reddit_client_secret),
                    headers={"User-Agent": getattr(settings, 'reddit_user_agent', 'AgoraObservatory/1.0')},
                )
                resp.raise_for_status()
                self._token = resp.json().get("access_token")
                return self._token
        except Exception as e:
            print(f"[RedditConnector] Token error: {e}")
            return None

    async def fetch(self, query: str, max_results: int = 100) -> list[RawPost]:
        if not self.is_configured:
            return []

        token = await self._get_token()
        if not token:
            return []

        posts = []
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": getattr(settings, 'reddit_user_agent', 'AgoraObservatory/1.0'),
        }

        async with httpx.AsyncClient(timeout=20) as client:
            # Search across relevant subreddits
            for subreddit in SUBREDDITS[:3]:
                try:
                    resp = await client.get(
                        f"https://oauth.reddit.com/r/{subreddit}/search",
                        params={"q": query, "limit": 25, "sort": "new", "restrict_sr": "on"},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        for item in resp.json().get("data", {}).get("children", []):
                            d = item.get("data", {})
                            text = f"{d.get('title','')} {d.get('selftext','')[:500]}".strip()
                            if not text:
                                continue
                            created = d.get("created_utc")
                            pub_dt = datetime.fromtimestamp(created, tz=timezone.utc) if created else None
                            posts.append(RawPost(
                                platform=self.platform,
                                external_id=d.get("id", ""),
                                content_text=text[:2000],
                                url=f"https://reddit.com{d.get('permalink','')}",
                                language="en",
                                published_at=pub_dt,
                                query_tag=query,
                            ))
                except Exception as e:
                    print(f"[RedditConnector] r/{subreddit} error: {e}")

            # Also search all of Reddit
            try:
                resp = await client.get(
                    "https://oauth.reddit.com/search",
                    params={"q": query + " Nigeria", "limit": 25, "sort": "new"},
                    headers=headers,
                )
                if resp.status_code == 200:
                    for item in resp.json().get("data", {}).get("children", []):
                        d = item.get("data", {})
                        text = f"{d.get('title','')} {d.get('selftext','')[:500]}".strip()
                        if not text:
                            continue
                        created = d.get("created_utc")
                        pub_dt = datetime.fromtimestamp(created, tz=timezone.utc) if created else None
                        posts.append(RawPost(
                            platform=self.platform,
                            external_id=d.get("id", "") + "_global",
                            content_text=text[:2000],
                            url=f"https://reddit.com{d.get('permalink','')}",
                            language="en",
                            published_at=pub_dt,
                            query_tag=query,
                        ))
            except Exception as e:
                print(f"[RedditConnector] global search error: {e}")

        return posts[:max_results]
