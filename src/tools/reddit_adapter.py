import httpx
import feedparser
import logging
from typing import List
from datetime import datetime
from src.tools.base_adapter import SourceAdapter
from src.models.items import IngestedItem
from src.feeds_config import DEFAULT_SUBREDDITS

logger = logging.getLogger(__name__)

class RedditAdapter(SourceAdapter):
    def __init__(self, feed_urls: List[str] = None):
        self.feed_urls = feed_urls or DEFAULT_SUBREDDITS

    async def fetch_items(self, lookback_hours: int = 24) -> List[IngestedItem]:
        logger.info(f"Fetching Reddit feeds: {len(self.feed_urls)} sources")
        items = []
        
        # Reddit requires a custom User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            for url in self.feed_urls:
                try:
                    # Reddit RSS often redirects to a confirmation page if not handled right, 
                    # but usually strict user-agent fixes it.
                    resp = await client.get(url, timeout=10.0)
                    if resp.status_code == 200:
                        feed = feedparser.parse(resp.content)
                        for entry in feed.entries:
                            # Reddit RSS 'updated' is usually present
                            published = entry.get('updated_parsed') or entry.get('published_parsed')
                            if published:
                                dt = datetime(*published[:6])
                            else:
                                dt = datetime.utcnow()

                            if (datetime.utcnow() - dt).total_seconds() > lookback_hours * 3600:
                                continue
                            
                            # Content in Reddit RSS is HTML encoded in 'content' or 'summary'
                            content = entry.get('content', [{'value': ''}])[0]['value'] or entry.get('summary', '')
                            
                            items.append(IngestedItem(
                                source="Reddit",
                                title=entry.get('title', 'No Title'),
                                url=entry.get('link', ''),
                                content=content,
                                author=entry.get('author', 'Unknown Redditor'),
                                created_at=dt,
                                metadata={"feed_url": url, "subreddit": feed.feed.get("title", "")}
                            ))
                    else:
                        logger.warning(f"Reddit fetch failed {url} status {resp.status_code}")
                except Exception as e:
                    logger.warning(f"Failed to fetch Reddit {url}: {e}")
        
        logger.info(f"Found {len(items)} Reddit items")
        return items
