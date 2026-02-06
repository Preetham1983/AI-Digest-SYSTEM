from typing import List
import numpy as np
from src.models.items import IngestedItem
from src.services.logger import logger
from src.services.embedding import get_embedding, get_embeddings_batch, get_model

# Anchor concepts representing the ideal content for each persona
ANCHORS = {
    "GENAI": "Technical details about Large Language Models, AI agents, RAG systems, transformer architectures, new model releases like Llama, GPT, Claude, Gemini, fine-tuning, prompt engineering, AI research breakthroughs.",
    "PRODUCT": "New software startup ideas, B2B SaaS opportunities, market gaps, product launches, innovative apps, developer tools, problems enabling new product development, tech entrepreneurship.",
    "FINANCE": "Financial reports of tech companies, revenue data, funding rounds, IPOs, stock market analysis, AI company valuations, venture capital investments, earnings reports.",
}

class SemanticPrefilter:
    def __init__(self):
        self.anchor_embeddings = {}
        self._initialized = False
    
    def _initialize_anchors(self):
        """Pre-compute embeddings for anchors using shared model."""
        if self._initialized:
            return
        
        # This will load the shared model if not already loaded
        logger.info("Computing prefilter anchor embeddings...")
        
        for key, text in ANCHORS.items():
            emb = get_embedding(text, normalize=True)
            self.anchor_embeddings[key] = emb
        
        self._initialized = True
        logger.info("✅ Semantic prefilter ready!")
    
    async def is_relevant(self, item: IngestedItem, threshold: float = 0.35) -> bool:
        """
        Checks if item is semantically similar to ANY of the persona anchors.
        Uses cosine similarity with normalized embeddings.
        """
        # Initialize on first call
        if not self._initialized:
            self._initialize_anchors()
        
        # Combine title and content for embedding
        text = (item.title + " " + (item.content or ""))[:512]
        
        # Get embedding using shared model
        item_emb = get_embedding(text, normalize=True)
        
        # Check similarity against all anchors
        max_score = -1.0
        
        for key, anchor_emb in self.anchor_embeddings.items():
            score = np.dot(item_emb, anchor_emb)
            if score > max_score:
                max_score = score
        
        # Keep if above threshold OR high engagement score
        if max_score >= threshold:
            return True
        
        # Fallback: Keep high-engagement items regardless of semantic match
        if item.raw_score and item.raw_score > 100:
            return True
            
        return False
    
    async def filter_batch(self, items: List[IngestedItem], threshold: float = 0.35) -> List[IngestedItem]:
        """
        Batch filter for efficiency - encodes all items at once using shared model.
        """
        if not self._initialized:
            self._initialize_anchors()
        
        if not items:
            return []
        
        # Batch encode all items using shared model
        texts = [(item.title + " " + (item.content or ""))[:512] for item in items]
        item_embeddings = get_embeddings_batch(texts, normalize=True, show_progress=False)
        
        # Stack anchor embeddings
        anchor_keys = list(self.anchor_embeddings.keys())
        anchor_matrix = np.stack([self.anchor_embeddings[k] for k in anchor_keys])
        
        # Compute all similarities at once: (num_items, num_anchors)
        similarities = np.dot(item_embeddings, anchor_matrix.T)
        max_scores = np.max(similarities, axis=1)
        
        # Filter items
        relevant = []
        for i, item in enumerate(items):
            if max_scores[i] >= threshold:
                relevant.append(item)
            elif item.raw_score and item.raw_score > 100:
                relevant.append(item)
        
        logger.info(f"Semantic prefilter: {len(relevant)}/{len(items)} items passed (threshold={threshold})")
        return relevant

# Global instance
prefilter = SemanticPrefilter()
