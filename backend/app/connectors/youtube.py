"""
YouTube Data API v3 connector.
Fetches public video metadata only — no author PII stored.
Requires: YOUTUBE_API_KEY env var.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector, RawPost
from app.core.config import get_settings

settings = get_settings()

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeConnector(BaseConnector):
    platform = "youtube"

    @property
    def is_configured(self) -> bool:
        return bool(settings.youtube_api_key)

    async def fetch(self, query: str, max_results: int = 50) -> list[RawPost]:
        if not self.is_configured:
            return []

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Search for videos
                search_resp = await client.get(YOUTUBE_SEARCH_URL, params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": min(max_results, 50),
                    "order": "date",
                    "key": settings.youtube_api_key,
                })
                search_resp.raise_for_status()
                data = search_resp.json()

                posts = []
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = item.get("id", {}).get("videoId", "")
                    if not video_id:
                        continue

                    published = snippet.get("publishedAt", "")
                    pub_dt: Optional[datetime] = None
                    if published:
                        try:
                            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    # Combine title + description for NLP — no author stored
                    text = f"{snippet.get('title', '')} {snippet.get('description', '')}"

                    posts.append(RawPost(
                        platform=self.platform,
                        external_id=video_id,
                        content_text=text[:2000],
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                        published_at=pub_dt,
                        query_tag=query,
                    ))

                return posts

        except (httpx.HTTPError, Exception) as e:
            print(f"[YouTubeConnector] fetch failed: {e}")
            return []
