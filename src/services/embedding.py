"""
Shared Embedding Service - Singleton for all-MiniLM-L6-v2
Used by: prefilter, evaluator, vector_store
"""
from sentence_transformers import SentenceTransformer
from src.services.logger import logger
import numpy as np
from typing import List, Union

# Singleton instance
_model = None
_initialized = False

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension

def get_model() -> SentenceTransformer:
    """Get shared embedding model (lazy loaded singleton)"""
    global _model, _initialized
    
    if not _initialized:
        logger.info("🔄 Loading shared embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        _initialized = True
        logger.info("✅ Embedding model loaded! (384 dimensions)")
    
    return _model


def get_embedding(text: str, normalize: bool = True) -> np.ndarray:
    """Get embedding for a single text"""
    model = get_model()
    return model.encode(text, normalize_embeddings=normalize)


def get_embeddings_batch(texts: List[str], normalize: bool = True, show_progress: bool = False) -> np.ndarray:
    """Get embeddings for multiple texts (batch mode - faster)"""
    model = get_model()
    return model.encode(texts, normalize_embeddings=normalize, show_progress_bar=show_progress)


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two normalized embeddings"""
    return float(np.dot(embedding1, embedding2))


def get_dimension() -> int:
    """Get embedding dimension"""
    return EMBEDDING_DIM
