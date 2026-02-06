from abc import ABC, abstractmethod
from typing import List
from src.models.items import IngestedItem

class SourceAdapter(ABC):
    @abstractmethod
    async def fetch_items(self, lookback_hours: int = 24) -> List[IngestedItem]:
        pass
