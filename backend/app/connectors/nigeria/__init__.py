"""
Nigeria Media Connector Framework
Pluggable RSS/API connectors for Nigerian and diaspora media outlets.
Each outlet is an independent module — add new ones without refactoring.
All use official RSS feeds or public APIs only.
"""
import httpx
from datetime import datetime, timezone
from typing import Optional
from xml.etree import ElementTree

from app.connectors.base import BaseConnector, RawPost


# ─── Base RSS connector (reusable for any RSS feed) ───────────────────────────

class RSSConnector(BaseConnector):
    """Generic RSS feed connector. Subclass and set feed_url + platform."""
    feed_url: str = ""
    platform: str = "rss"

    @property
    def is_configured(self) -> bool:
        return bool(self.feed_url)

    async def fetch(self, query: str, max_results: int = 50) -> list[RawPost]:
        if not self.feed_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(self.feed_url, headers={"User-Agent": "AgoraObservatory/1.0"})
                resp.raise_for_status()
                return self._parse_rss(resp.text, query, max_results)
        except Exception as e:
            print(f"[{self.__class__.__name__}] fetch failed: {e}")
            return []

    def _parse_rss(self, xml_text: str, query: str, max_results: int) -> list[RawPost]:
        posts = []
        try:
            root = ElementTree.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//item") or root.findall(".//atom:entry", ns)

            for item in items[:max_results]:
                def get(tag):
                    el = item.find(tag)
                    return el.text.strip() if el is not None and el.text else ""

                title = get("title")
                description = get("description") or get("summary")
                link = get("link") or get("guid")
                pub_date = get("pubDate") or get("published") or get("updated")

                pub_dt: Optional[datetime] = None
                if pub_date:
                    for fmt in [
                        "%a, %d %b %Y %H:%M:%S %z",
                        "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%SZ",
                    ]:
                        try:
                            pub_dt = datetime.strptime(pub_date.strip(), fmt)
                            if pub_dt.tzinfo is None:
                                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue

                text = f"{title} {description}".strip()[:2000]
                if not text:
                    continue

                posts.append(RawPost(
                    platform=self.platform,
                    external_id=link or f"{self.platform}_{hash(text)}",
                    content_text=text,
                    url=link,
                    language="en",
                    published_at=pub_dt,
                    query_tag=query,
                ))
        except ElementTree.ParseError as e:
            print(f"[{self.__class__.__name__}] XML parse error: {e}")
        return posts


# ─── Nigerian media outlets ───────────────────────────────────────────────────
# Add new outlets here as independent classes. Each is auto-discovered.

class PunchNigeriaConnector(RSSConnector):
    """Punch Nigeria — leading Nigerian newspaper RSS feed."""
    platform = "punch_nigeria"
    feed_url = "https://punchng.com/feed/"


class VanguardNigeriaConnector(RSSConnector):
    """Vanguard Nigeria RSS feed."""
    platform = "vanguard_nigeria"
    feed_url = "https://www.vanguardngr.com/feed/"


class ThisDayNigeriaConnector(RSSConnector):
    """ThisDay Nigeria RSS feed."""
    platform = "thisday_nigeria"
    feed_url = "https://www.thisdaylive.com/index.php/feed/"


class PremiumTimesNigeriaConnector(RSSConnector):
    """Premium Times Nigeria RSS feed."""
    platform = "premium_times"
    feed_url = "https://www.premiumtimesng.com/feed"


class NairameticsConnector(RSSConnector):
    """Nairametrics — Nigerian finance and business news."""
    platform = "nairametrics"
    feed_url = "https://nairametrics.com/feed/"


class AfricanArgumentsConnector(RSSConnector):
    """African Arguments — pan-African analysis."""
    platform = "african_arguments"
    feed_url = "https://africanarguments.org/feed/"


class BBCAfricaConnector(RSSConnector):
    """BBC Africa RSS feed."""
    platform = "bbc_africa"
    feed_url = "https://feeds.bbci.co.uk/news/world/africa/rss.xml"


class VOAAfricaConnector(RSSConnector):
    """Voice of America Africa RSS."""
    platform = "voa_africa"
    feed_url = "https://www.voanews.com/api/zkokmkmppe"



class DailyTrustConnector(RSSConnector):
    """Daily Trust Nigeria RSS feed."""
    platform = "daily_trust"
    feed_url = "https://dailytrust.com/feed/"


class ChannelsTelevisionConnector(RSSConnector):
    """Channels Television Nigeria RSS feed."""
    platform = "channels_tv"
    feed_url = "https://www.channelstv.com/feed/"


class BusinessDayNigeriaConnector(RSSConnector):
    """BusinessDay Nigeria — business and economic news."""
    platform = "businessday_nigeria"
    feed_url = "https://businessday.ng/feed/"


# ─── Registry of all Nigeria/Africa connectors ───────────────────────────────
# Simply add new connector classes above and list them here.

NIGERIA_CONNECTORS: list[BaseConnector] = [
    PunchNigeriaConnector(),
    VanguardNigeriaConnector(),
    ThisDayNigeriaConnector(),
    PremiumTimesNigeriaConnector(),
    NairameticsConnector(),
    AfricanArgumentsConnector(),
    BBCAfricaConnector(),
    VOAAfricaConnector(),
    DailyTrustConnector(),
    ChannelsTelevisionConnector(),
    BusinessDayNigeriaConnector(),
]


def get_nigeria_connector_status() -> list[dict]:
    return [
        {"platform": c.platform, "configured": c.is_configured, "type": "rss"}
        for c in NIGERIA_CONNECTORS
    ]
