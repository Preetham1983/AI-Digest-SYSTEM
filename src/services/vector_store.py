import faiss
import numpy as np
import pickle
import os
from src.config import settings
from typing import List, Tuple
from src.services.logger import logger
from src.services.embedding import get_embedding, get_embeddings_batch, get_dimension, EMBEDDING_DIM

INDEX_FILE = settings.DATA_DIR / "vector_index.faiss"
ID_MAP_FILE = settings.DATA_DIR / "vector_ids.pkl"

class VectorStore:
    def __init__(self):
        self.dimension = EMBEDDING_DIM  # 384 for all-MiniLM-L6-v2
        self._needs_rebuild = False
        
        # Check if index exists
        if os.path.exists(INDEX_FILE) and os.path.exists(ID_MAP_FILE):
            self.load_index()
            # Check if dimension mismatch (old 4096 vs new 384)
            if self.index.d != self.dimension:
                logger.warning(f"⚠️ Index dimension mismatch! Found {self.index.d}, expected {self.dimension}")
                logger.warning("🔄 Creating new index with correct dimensions...")
                self._rebuild_index()
        else:
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product for cosine sim
            self.stored_ids = []
        
        self.id_set = set(self.stored_ids)  # Fast lookup
        logger.info(f"VectorStore initialized with {self.index.ntotal} items ({self.dimension} dim).")
    
    def _rebuild_index(self):
        """Rebuild index with new dimensions (clears old data)"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.stored_ids = []
        self.id_set = set()
        self._needs_rebuild = True
        logger.info("✅ New index created. Old vectors cleared (dimension changed).")

    def save_index(self):
        try:
            faiss.write_index(self.index, str(INDEX_FILE))
            with open(ID_MAP_FILE, "wb") as f:
                pickle.dump(self.stored_ids, f)
            logger.info("Vector index saved.")
        except Exception as e:
            logger.error(f"Failed to save vector index: {e}")

    def load_index(self):
        try:
            self.index = faiss.read_index(str(INDEX_FILE))
            with open(ID_MAP_FILE, "rb") as f:
                self.stored_ids = pickle.load(f)
            self.id_set = set(self.stored_ids)
        except Exception as e:
            logger.error(f"Failed to load vector index: {e}")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.stored_ids = []
            self.id_set = set()

    def has_id(self, id: str) -> bool:
        return id in self.id_set

    def get_embedding_sync(self, text: str) -> np.ndarray:
        """Get embedding using shared local model (FAST - no API call)"""
        return get_embedding(text[:512], normalize=True)
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """Async wrapper for compatibility (actually sync, but fast)"""
        return self.get_embedding_sync(text)

    def add_item_sync(self, id: str, text: str, embedding: np.ndarray = None):
        """Add item synchronously (fast)"""
        if embedding is not None:
            emb = embedding
        else:
            emb = self.get_embedding_sync(text)
        
        # Ensure normalized for cosine similarity
        vec = np.array([emb], dtype='float32')
        self.index.add(vec)
        self.stored_ids.append(id)
        self.id_set.add(id)

    async def add_item(self, id: str, text: str, embedding: np.ndarray = None):
        """Async wrapper for compatibility"""
        self.add_item_sync(id, text, embedding)
        
    async def is_duplicate(self, text: str, threshold: float = 0.85, embedding: np.ndarray = None) -> bool:
        """
        Checks if a semantically similar item exists.
        Uses cosine similarity (IndexFlatIP with normalized vectors).
        Threshold: 0.85 = 85% similar (high = stricter)
        """
        if self.index.ntotal == 0:
            return False
        
        if embedding is not None:
            emb = embedding
        else:
            emb = self.get_embedding_sync(text)
        
        vec = np.array([emb], dtype='float32')
        
        # Search for 1 nearest neighbor (returns cosine similarity for IndexFlatIP)
        similarities, indices = self.index.search(vec, 1)
        
        similarity = similarities[0][0]
        
        # Cosine similarity: 1.0 = identical, 0 = unrelated
        if similarity >= threshold:
            return True
        return False
    
    def is_duplicate_sync(self, text: str, threshold: float = 0.85) -> bool:
        """Sync version of duplicate check"""
        if self.index.ntotal == 0:
            return False
        
        emb = self.get_embedding_sync(text)
        vec = np.array([emb], dtype='float32')
        similarities, _ = self.index.search(vec, 1)
        return similarities[0][0] >= threshold
        
    async def search(self, text: str, k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar items, returns (id, similarity_score) tuples"""
        emb = self.get_embedding_sync(text)
        vec = np.array([emb], dtype='float32')
        similarities, indices = self.index.search(vec, k)
        
        results = []
        for sim, idx in zip(similarities[0], indices[0]):
            if idx != -1 and idx < len(self.stored_ids):
                results.append((self.stored_ids[idx], float(sim)))
        return results

# Global instance
vector_store = VectorStore()
