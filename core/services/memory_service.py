import os
from mem0 import Memory
from typing import List, Dict, Any, Optional

class MemoryService:
    """
    Standardized service for Long-term Memory using Mem0.
    Stores and retrieves user facts, preferences, and progress.
    """
    def __init__(self):
        # Configuration for Mem0
        # Uses local ChromaDB by default if no host is provided
        config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "path": os.getenv("CHROMA_DB_PATH", "chroma_db"),
                }
            }
        }
        self.memory = Memory.from_config(config)

    def add_memory(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Adds a new fact or interaction to long-term memory."""
        print(f"  [MemoryService] Adding memory for user {user_id}...")
        return self.memory.add(text, user_id=user_id, metadata=metadata)

    def search_memory(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves relevant facts from long-term memory."""
        print(f"  [MemoryService] Searching memory for user {user_id}: {query}...")
        return self.memory.search(query, user_id=user_id, limit=limit)

    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all stored facts for a user."""
        return self.memory.get_all(user_id=user_id)

    def delete_memory(self, memory_id: str):
        """Deletes a specific memory entry."""
        return self.memory.delete(memory_id)

    def reset_memory(self, user_id: str):
        """Wipes all memory for a user."""
        return self.memory.delete_all(user_id=user_id)

# Singleton instance
memory_service = MemoryService()
