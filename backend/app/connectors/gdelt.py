"""
GDELT 2.0 GKG (Global Knowledge Graph) connector.
Completely free, no API key required — open public data.
https://www.gdeltproject.org/
Fetches recent news articles matching a query via the GDELT DOC API.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector, RawPost

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTConnector(BaseConnector):
    platform = "gdelt"

    @property
    def is_configured(self) -> bool:
        return True  # No credentials needed

    async def fetch(self, query: str, max_results: int = 100) -> list[RawPost]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(GDELT_DOC_API, params={
                    "query": query,
                    "mode": "artlist",
                    "maxrecords": min(max_results, 250),
                    "format": "json",
                    "sort": "datedesc",
                })
                resp.raise_for_status()
                data = resp.json()

                posts = []
                for article in data.get("articles", []):
                    pub_str = article.get("seendate", "")
                    pub_dt: Optional[datetime] = None
                    if pub_str:
                        try:
                            pub_dt = datetime.strptime(pub_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                        except ValueError:
                            pass

                    title = article.get("title", "")
                    url = article.get("url", "")

                    posts.append(RawPost(
                        platform=self.platform,
                        external_id=url[:200] or f"gdelt_{hash(title)}",
                        content_text=title[:1000],
                        url=url,
                        language=article.get("language", "en"),
                        published_at=pub_dt,
                        query_tag=query,
                    ))

                return posts

        except (httpx.HTTPError, Exception) as e:
            print(f"[GDELTConnector] fetch failed: {e}")
            return []
