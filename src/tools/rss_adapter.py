import httpx
import feedparser
import logging
from typing import List
from datetime import datetime
from email.utils import parsedate_to_datetime
from src.tools.base_adapter import SourceAdapter
from src.models.items import IngestedItem
from src.feeds_config import DEFAULT_RSS_FEEDS

logger = logging.getLogger(__name__)

class RSSAdapter(SourceAdapter):
    def __init__(self, feed_urls: List[str] = None):
        self.feed_urls = feed_urls or DEFAULT_RSS_FEEDS

    async def fetch_items(self, lookback_hours: int = 168) -> List[IngestedItem]:
        logger.info(f"Fetching RSS feeds: {len(self.feed_urls)} sources")
        items = []
        async with httpx.AsyncClient() as client:
            for url in self.feed_urls:
                try:
                    resp = await client.get(url, timeout=10.0)
                    if resp.status_code == 200:
                        feed = feedparser.parse(resp.content)
                        for entry in feed.entries:
                            # Parse time
                            published = entry.get('published_parsed') or entry.get('updated_parsed')
                            if published:
                                dt = datetime(*published[:6])
                            else:
                                dt = datetime.utcnow() # Fallback

                            # Check age
                            if (datetime.utcnow() - dt).total_seconds() > lookback_hours * 3600:
                                continue
                            
                            items.append(IngestedItem(
                                source="RSS",
                                title=entry.get('title', 'No Title'),
                                url=entry.get('link', ''),
                                content=entry.get('summary', '') or entry.get('description', ''),
                                author=feed.feed.get('title', 'Unknown RSS'),
                                created_at=dt,
                                metadata={"feed_url": url}
                            ))
                except Exception as e:
                    logger.warning(f"Failed to fetch RSS {url}: {e}")
        
        logger.info(f"Found {len(items)} RSS items")
        return items
