import os
import json
import numpy as np
import uuid
from typing import List, Dict, Any, Optional
from core.utils.llm_manager import LLMManager
from core.utils.bot_logger import get_logger

logger = get_logger("vector_store_kinh_dich")

class ChromaKinhDichStore:
    """
    Specialized Vector Store for Kinh Dịch (I Ching).
    Handles semantic search for hexagrams, yao (lines), and general theory.
    """
    def __init__(self, persist_directory=None):
        if persist_directory is None:
            # Save inside the Orchesta data directory (same as Scholar Agent's general location)
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            persist_directory = os.path.join(base_dir, "data", "chroma_kinh_dich")
            
        self.persist_directory = persist_directory
        self.backup_file = os.path.join(persist_directory, "kinhdich_store.json")
        self.embedding_file = os.path.join(persist_directory, "embeddings_cache.npy")
        
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)

        self.llm = LLMManager()
        self.chunks: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, List[float]] = {}
        self.query_cache: Dict[str, List[float]] = {} # Simple in-memory cache for search queries
        self._load_store()

    def _load_store(self):
        """Load chunks and embeddings from disk."""
        if os.path.exists(self.backup_file):
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                try:
                    self.chunks = json.load(f)
                except Exception as e:
                    logger.warning(f"Error loading chunks: {e}")
                    self.chunks = {}
        
        if os.path.exists(self.embedding_file):
            try:
                self.embeddings = np.load(self.embedding_file, allow_pickle=True).item()
            except Exception as e:
                logger.warning(f"Error loading embeddings: {e}")
                self.embeddings = {}

    def _save_store(self):
        """Persist chunks and embeddings to disk."""
        with open(self.backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        
        np.save(self.embedding_file, self.embeddings)

    def add_chunk(self, content: str, metadata: Dict[str, Any], save: bool = True):
        """Adds a text chunk with metadata and generates its embedding."""
        chunk_id = str(uuid.uuid4())
        
        # 1. Save data
        self.chunks[chunk_id] = {
            "content": content,
            "metadata": metadata
        }
        
        # 2. Generate Embedding
        # We include key metadata in the text to embed to improve search
        text_to_embed = f"{metadata.get('category', '')} {metadata.get('title', '')} {content}"
        embedding = self.llm.embed(text_to_embed)
        
        if embedding:
            self.embeddings[chunk_id] = embedding
            if save:
                self._save_store()
            return chunk_id
        return None

    def search(self, query: str, category: Optional[str] = None, n_results=5) -> List[Dict[str, Any]]:
        """
        Semantic Search for Kinh Dịch content.
        """
        if not self.chunks:
            return []

        if query in self.query_cache:
            query_vector = self.query_cache[query]
        else:
            query_vector = self.llm.embed(query)
            if query_vector:
                self.query_cache[query] = query_vector
        
        if not query_vector:
            return []
            
        scored_results = []
        for chunk_id, chunk in self.chunks.items():
            # Apply category filter if provided
            if category and chunk["metadata"].get("category") != category:
                continue

            # Semantic Score (Cosine Similarity)
            semantic_score = 0
            if chunk_id in self.embeddings:
                v1 = np.array(query_vector)
                v2 = np.array(self.embeddings[chunk_id])
                if np.any(v1) and np.any(v2):
                    semantic_score = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            # Optional: Add metadata weighting? 
            # For now just pure semantic
            scored_results.append((semantic_score, chunk))

        # Sort by total score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [item[1] for item in scored_results[:n_results] if item[0] > 0.4] # High threshold for accuracy

    def clear_all(self):
        """Resets the store."""
        self.chunks = {}
        self.embeddings = {}
        if os.path.exists(self.backup_file): os.remove(self.backup_file)
        if os.path.exists(self.embedding_file): os.remove(self.embedding_file)
        print("  [KinhDichStore] Storage cleared.")
