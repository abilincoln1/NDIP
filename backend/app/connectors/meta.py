"""
Meta Graph API connector.
Fetches posts from Facebook Pages and Instagram Business Accounts YOU own/manage.
Requires: META_ACCESS_TOKEN and META_PAGE_IDS env vars.
Only accesses pages you have admin rights to — no public scraping.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector, RawPost
from app.core.config import get_settings

settings = get_settings()
GRAPH_BASE = "https://graph.facebook.com/v19.0"


class MetaConnector(BaseConnector):
    platform = "meta"

    @property
    def is_configured(self) -> bool:
        return bool(getattr(settings, 'meta_access_token', '') and
                    getattr(settings, 'meta_page_ids', ''))

    async def fetch(self, query: str, max_results: int = 100) -> list[RawPost]:
        if not self.is_configured:
            return []

        token = settings.meta_access_token
        page_ids = [p.strip() for p in settings.meta_page_ids.split(",") if p.strip()]
        posts = []

        async with httpx.AsyncClient(timeout=20) as client:
            for page_id in page_ids:
                try:
                    resp = await client.get(
                        f"{GRAPH_BASE}/{page_id}/posts",
                        params={
                            "fields": "id,message,story,created_time,permalink_url",
                            "limit": min(max_results, 100),
                            "access_token": token,
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    for item in data.get("data", []):
                        text = item.get("message") or item.get("story") or ""
                        created = item.get("created_time", "")
                        pub_dt: Optional[datetime] = None
                        if created:
                            try:
                                pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            except ValueError:
                                pass

                        posts.append(RawPost(
                            platform=self.platform,
                            external_id=item["id"],
                            content_text=text[:2000],
                            url=item.get("permalink_url"),
                            language="en",
                            published_at=pub_dt,
                            query_tag=f"page:{page_id}",
                        ))
                except (httpx.HTTPError, Exception) as e:
                    print(f"[MetaConnector] page {page_id} failed: {e}")

        return posts
