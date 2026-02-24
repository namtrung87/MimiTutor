import os
import json
from mem0 import Memory
from dotenv import load_dotenv

load_dotenv()

class MemoryManager:
    """
    Handles long-term memory across sessions using Mem0ai.
    Stores and retrieves user preferences, past interactions, and distilled facts.
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
                        "path": "./.mem0_db",
                    }
                },
                "llm": {
                    "provider": "google",
                    "config": {
                        "model": "gemini-3-flash-preview",
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
            except:
                return []
        return []

    def _save_mock_db(self):
        try:
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(self.mock_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  [Memory] Failed to save mock db: {e}")

    def add_memory(self, data, user_id, metadata=None):
        """Adds a new interaction to long-term memory."""
        print(f"  [Memory] Adding context for user: {user_id}")
        # Phase 13: Memory Hygiene
        # Prevent saving system errors to long-term memory
        if isinstance(data, str) and ("Error parsing JSON" in data or "Unparseable output" in data):
            print(f"  [Memory] Skipped adding corrupted memory: {data[:50]}...")
            return False

        if self.is_mock:
            self.mock_db.append({"text": str(data), "user_id": user_id, "metadata": metadata})
            self._save_mock_db()
            self._sync_to_brain_md(user_id)
            return True
        result = self.memory.add(data, user_id=user_id, metadata=metadata)
        self._sync_to_brain_md(user_id)
        return result

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
                for m in memories:
                    text = m.get('memory') or m.get('text')
                    f.write(f"- {text}\n")
            print(f"  [Memory] Synchronized to {brain_path}")
        except Exception as e:
            print(f"  [Memory] Error syncing to BRAIN.md: {e}")

    def search_memories(self, query, user_id, limit=5):
        """Retrieves relevant memories for a given query."""
        print(f"  [Memory] Searching history for: {query[:30]}...")
        if self.is_mock:
            # Simple keyword match mock
            query_words = query.lower().split()
            results = []
            for m in self.mock_db:
                if m.get("user_id") == user_id:
                    score = sum(1 for word in query_words if word in m["text"].lower())
                    if score > 0:
                        results.append((score, m))
            # Sort by "relevance" (score)
            results.sort(key=lambda x: x[0], reverse=True)
            return [m for score, m in results][:limit]
        return self.memory.search(query, user_id=user_id, limit=limit)

    def get_all_memories(self, user_id):
        """Gets the full distilled profile for a user."""
        if self.is_mock: return [m for m in self.mock_db if m.get("user_id") == user_id]
        return self.memory.get_all(user_id=user_id)

    def delete_all_memories(self, user_id):
        """Resets user memory."""
        if self.is_mock: 
            self.mock_db = [m for m in self.mock_db if m.get("user_id") != user_id]
            self._save_mock_db()
        else: self.memory.delete_all(user_id=user_id)

memory_manager = MemoryManager()
