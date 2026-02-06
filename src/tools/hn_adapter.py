import httpx
import logging
import asyncio
from typing import List
from datetime import datetime, timedelta
from src.tools.base_adapter import SourceAdapter
from src.models.items import IngestedItem

logger = logging.getLogger(__name__)

class HackerNewsAdapter(SourceAdapter):
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    async def fetch_items(self, lookback_hours: int = 24) -> List[IngestedItem]:
        logger.info(f"Fetching HN stories (lookback={lookback_hours}h)")
        async with httpx.AsyncClient() as client:
            # unique set of ids from top, best, and show
            ids = set()
            for endpoint in ["topstories", "showstories"]:
                resp = await client.get(f"{self.BASE_URL}/{endpoint}.json")
                if resp.status_code == 200:
                    ids.update(resp.json()[:30]) # First 30 from each to keep it fast but broad

            items = []
            
            # Fetch details in parallel
            tasks = [self._fetch_item(client, id) for id in ids]
            results = await asyncio.gather(*tasks)
            
            cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
            
            for item in results:
                if item and item.created_at > cutoff:
                    items.append(item)
            
            logger.info(f"Found {len(items)} relevant HN items")
            return items

    async def _fetch_item(self, client, id) -> IngestedItem | None:
        try:
            resp = await client.get(f"{self.BASE_URL}/item/{id}.json")
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data or data.get("type") != "story":
                return None
            
            # timestamp is unix 
            dt = datetime.utcfromtimestamp(data.get("time", 0))
            
            return IngestedItem(
                source="HackerNews",
                title=data.get("title", ""),
                url=data.get("url", f"https://news.ycombinator.com/item?id={id}"),
                content=data.get("text", ""), # some Ask HN have text
                author=data.get("by"),
                created_at=dt,
                raw_score=data.get("score", 0),
                metadata={"hn_id": id, "comments": data.get("descendants", 0), "score": data.get("score", 0)}
            )
        except Exception as e:
            logger.error(f"Error fetching HN item {id}: {e}")
            return None
