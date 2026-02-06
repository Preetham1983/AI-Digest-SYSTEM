
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class IngestedItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    title: str
    url: str
    content: Optional[str] = None # Text content or description
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    raw_score: Optional[int] = 0 # e.g. upvotes
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None # Cached vector
    
    def to_prompt_string(self) -> str:
        snippet = (self.content or "")[:400].replace("\n", " ")
        return f"ID: {self.id} | TITLE: {self.title} | SOURCE: {self.source} | CONTENT: {snippet}"

class EvaluationResult(BaseModel):
    item_id: str
    persona: str
    score: float
    decision: str # KEEP, DISCARD
    reasoning: str
    details: Dict[str, Any] # structured json from LLM
