import os
import json
from mem0 import Memory
from dotenv import load_dotenv

load_dotenv()

class MemoryManager:
    """
    Handles memory across 3 tiers:
    1. Working Memory (Session context - handled by state)
    2. Episodic Memory (Recent interactions - last 10-20)
    3. Semantic Memory (Permanent facts, preferences, lessons learned)
    """
    def __init__(self):
        # Define a stable path relative to the core directory
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.persist_path = os.path.join(root_dir, ".mock_memory.json")
        try:
            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "orchestra_memory",
                        "path": os.path.join(root_dir, ".mem0_db"),
                    }
                },
                "llm": {
                    "provider": "google",
                    "config": {
                        "model": "gemini-2.0-flash",
                        "temperature": 0,
                    }
                }
            }
            self.memory = Memory.from_config(config)
            self.is_mock = False
        except Exception as e:
            print(f"  [Memory] WARNING: Failed to initialize Mem0 ({e}). Using Persistent Mock Memory.")
            self.is_mock = True
            self.mock_db = self._load_mock_db()

    def _load_mock_db(self):
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  [Memory] Error loading mock db: {e}")
                return []
        return []

    def _save_mock_db(self):
        try:
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(self.mock_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [Memory] Failed to save mock db: {e}")

    def _load_distill_prompt(self):
        root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../"))
        prompt_path = os.path.join(root_dir, "prompts", "memory_distillation.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "Extract long-term facts from the interaction."

    async def distill_interaction(self, user_input, ai_response):
        """Uses LLM to extract key facts from an interaction before storing."""
        from core.utils.llm_manager import LLMManager
        llm = LLMManager()
        
        prompt_template = self._load_distill_prompt()
        prompt = prompt_template.format(user_input=user_input, ai_response=ai_response)
        
        try:
            raw_json = llm.query(prompt, complexity="L1")
            # Parse JSON safely
            clean_json = raw_json.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
            return json.loads(clean_json)
        except Exception as e:
            print(f"  [Memory] Distillation failed: {e}")
            return []

    async def add_memory(self, user_input, ai_response, user_id, metadata=None):
        """Adds a new interaction to long-term memory with distillation and similarity check."""
        print(f"  [Memory] Processing interaction for user: {user_id}")
        
        # 1. Distill key facts
        facts = await self.distill_interaction(user_input, ai_response)
        if not facts or not isinstance(facts, list):
            return False

        for fact in facts:
            # 2. Poison Marker Check
            POISON_MARKERS = [
                "Error parsing JSON", "Unparseable output",
                "cần thêm một chút thời gian", "đứt dòng suy nghĩ",
                "hỏi lại chị sau ít phút"
            ]
            if any(marker in fact for marker in POISON_MARKERS):
                continue

            # 3. Similarity Check
            # (Mem0 handles semantic deduplication, but we filter obvious noise here)
            if self.is_mock:
                self.mock_db.append({"text": fact, "user_id": user_id, "metadata": metadata})
            else:
                self.memory.add(fact, user_id=user_id, metadata=metadata)

        if self.is_mock:
            if len(self.mock_db) > 500:
                self.prune_memories(user_id)
            self._save_mock_db()
        
        self._sync_to_brain_md(user_id)
        return True

    def prune_memories(self, user_id, max_size=100):
        """
        Keeps only the most recent/relevant memories.
        In mock mode: simple truncation. In Mem0: logic for 'forgetting' can be added.
        """
        print(f"  [Memory] Pruning memories for {user_id}...")
        if self.is_mock:
            user_mems = [m for m in self.mock_db if m.get("user_id") == user_id]
            if len(user_mems) > max_size:
                # Keep last N
                others = [m for m in self.mock_db if m.get("user_id") != user_id]
                self.mock_db = others + user_mems[-max_size:]
                self._save_mock_db()
        else:
            # Mem0 manages its own 'recent' context via vector search, 
            # but we could implement explicit deletion of old indices here if needed.
            pass

    async def _decay_episodic_memory(self, user_id: str):
        """Reduces the weight or prunes very old episodic memories (simplified)."""
        if self.is_mock:
            # For mock, we already prune in add_memory if > 500
            return
        # In a real Mem0 setup, we might use temporal decay filters. 
        # For this version, we'll keep it as a placeholder for Sprint 3.
        pass

    def _sync_to_brain_md(self, user_id):
        """Synchronizes long-term memory to a human-readable BRAIN.md file."""
        try:
            memories = self.get_all_memories(user_id)
            brain_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../BRAIN.md"))
            with open(brain_path, "w", encoding="utf-8") as f:
                f.write("# Orchesta Assistant: Transparent Memory (BRAIN.md)\n\n")
                f.write("> This file enables transparency into what your agents remember. Feel free to edit it manually.\n\n")
                f.write("## Long-Term Memories\n")
                if not memories:
                    f.write("No memories found.\n")
                else:
                    for m in memories:
                        if isinstance(m, dict):
                            text = m.get('memory') or m.get('text')
                            if text:
                                f.write(f"- {text}\n")
            print(f"  [Memory] Synchronized to {brain_path}")
        except Exception as e:
            print(f"  [Memory] Error syncing to BRAIN.md: {e}")

    def search_memories(self, query, user_id, limit=10):
        """Retrieves relevant memories using tiered search (Semantic > Episodic)."""
        print(f"  [Memory] Tiered search for: {query[:30]}...")
        
        results = []
        if self.is_mock:
            query_words = query.lower().split()
            scored_results = []
            for m in self.mock_db:
                if m.get("user_id") == user_id:
                    # Score boost for semantic tier
                    tier_multiplier = 2.0 if m.get("metadata", {}).get("tier") == "semantic" else 1.0
                    score = sum(1 for word in query_words if word in m["text"].lower()) * tier_multiplier
                    if score > 0:
                        scored_results.append((score, m))
            scored_results.sort(key=lambda x: x[0], reverse=True)
            results = [res[1] for res in scored_results][:limit]
        else:
            try:
                # Query with preference for semantic if possible, or just unified search
                results = self.memory.search(query, user_id=user_id, limit=limit)
            except Exception:
                results = []
        
        return results

    def get_all_memories(self, user_id):
        """Gets the full distilled profile for a user."""
        if self.is_mock: 
            return [m for m in self.mock_db if m.get("user_id") == user_id]
        try:
            return self.memory.get_all(user_id=user_id)
        except Exception:
            return []

    async def archive_to_semantic(self, user_id: str, lesson: str):
        """Moves a reflection lesson into permanent Semantic Memory."""
        print(f"  [Memory] Archiving to Semantic: {lesson[:50]}...")
        metadata = {"tier": "semantic", "type": "lesson_learned"}
        if self.is_mock:
            self.mock_db.append({"text": lesson, "user_id": user_id, "metadata": metadata})
            self._save_mock_db()
        else:
            self.memory.add(lesson, user_id=user_id, metadata=metadata)
        self._sync_to_brain_md(user_id)

    def delete_all_memories(self, user_id):
        """Resets user memory."""
        if self.is_mock: 
            self.mock_db = [m for m in self.mock_db if m.get("user_id") != user_id]
            self._save_mock_db()
        else: self.memory.delete_all(user_id=user_id)

memory_manager = MemoryManager()
