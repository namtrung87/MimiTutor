import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from core.utils.llm_manager import LLMManager

class ChromaSkillStore:
    """
    Advanced Skill Store: Uses Gemini Embeddings for Semantic Search 
    combined with Keyword matching (Hybrid Search).
    """
    def __init__(self, persist_directory="chroma_knowledgedb"):
        self.persist_directory = persist_directory
        self.backup_file = os.path.join(persist_directory, "skills_store.json")
        self.embedding_file = os.path.join(persist_directory, "embeddings_cache.npy")
        
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)

        self.llm = LLMManager()
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, List[float]] = {}
        self._load_store()

    def _load_store(self):
        """Load skills and embeddings from disk."""
        if os.path.exists(self.backup_file):
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                try:
                    self.skills = json.load(f)
                except:
                    self.skills = {}
        
        if os.path.exists(self.embedding_file):
            try:
                # Load as a dictionary of {id: vector}
                self.embeddings = np.load(self.embedding_file, allow_pickle=True).item()
            except Exception as e:
                print(f"  [SkillStore] Error loading embeddings: {e}")
                self.embeddings = {}

    def _save_store(self):
        """Persist skills and embeddings to disk."""
        with open(self.backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.skills, f, ensure_ascii=False, indent=2)
        
        np.save(self.embedding_file, self.embeddings)

    def add_skill(self, skill_card: Dict[str, Any]):
        """Adds a skill to the store and generates its embedding."""
        skill_id = skill_card.get("title", "unknown").replace(" ", "_").lower()
        
        # 1. Save data
        self.skills[skill_id] = skill_card
        
        # 2. Generate Embedding (Semantic representation)
        text_to_embed = f"{skill_card.get('title', '')} {skill_card.get('logic_summary', '')}"
        print(f"  [SkillStore] Generating embedding for: {skill_card.get('title')}")
        embedding = self.llm.embed(text_to_embed)
        
        if embedding:
            self.embeddings[skill_id] = embedding
        
        self._save_store()
        return True

    def search_skills(self, query: str, n_results=3) -> List[Dict[str, Any]]:
        """
        Hybrid Search: Combines Keyword overlap and Semantic Similarity.
        """
        if not self.skills:
            return []

        # --- Part A: Keyword Search (BM25-lite) ---
        query_words = set(query.lower().split())
        stop_words = {"môn", "có", "những", "nào", "là", "của", "và", "trong", "cho", "với"}
        query_words = query_words - stop_words
        if not query_words: query_words = set(query.lower().split())

        # --- Part B: Semantic Search (Vectors) ---
        query_vector = self.llm.embed(query)
        
        scored_results = []
        for skill_id, skill in self.skills.items():
            # 1. Keyword Score
            target_text = (skill.get('title', '') + " " + skill.get('logic_summary', '')).lower()
            target_words = set(target_text.replace("_", " ").split())
            keyword_overlap = len(query_words.intersection(target_words))
            keyword_score = keyword_overlap / max(1, len(query_words)) # Normalize 0-1
            
            # 2. Semantic Score (Cosine Similarity)
            semantic_score = 0
            if query_vector and skill_id in self.embeddings:
                v1 = np.array(query_vector)
                v2 = np.array(self.embeddings[skill_id])
                # Ensure vectors are not zero
                if np.any(v1) and np.any(v2):
                    semantic_score = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            # 3. Combined Score (Weighted)
            # Semantic search is more robust for concepts, Keyword is better for specific terms/IDs
            total_score = (semantic_score * 0.7) + (keyword_score * 0.3)
            scored_results.append((total_score, skill))

        # Sort by total score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Filter out very low matches if needed, but for now just take top N
        return [item[1] for item in scored_results[:n_results] if item[0] > 0.1]

    def clear_all(self):
        """Resets the store."""
        self.skills = {}
        self.embeddings = {}
        if os.path.exists(self.backup_file): os.remove(self.backup_file)
        if os.path.exists(self.embedding_file): os.remove(self.embedding_file)
        print("  [SkillStore] Storage cleared.")
