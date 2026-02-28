from typing import List, Dict, Any
from core.utils.memory_manager import memory_manager

class MemoryRouter:
    """
    Logic to decide which tier of memory to query based on request complexity and intent.
    """
    @staticmethod
    async def get_context(query: str, user_id: str, complexity: str = "L1") -> str:
        """
        Retrieves context from appropriate tiers.
        - L1: Episodic only (fast)
        - L2+: Semantic + Episodic
        """
        limit = 5 if complexity == "L1" else 10
        memories = memory_manager.search_memories(query, user_id, limit=limit)
        
        if not memories:
            return ""
            
        context_parts = []
        for m in memories:
            tier = m.get("metadata", {}).get("tier", "episodic")
            text = m.get("memory") or m.get("text")
            if text:
                context_parts.append(f"[{tier.upper()}] {text}")
                
        return "\n".join(context_parts)

memory_router = MemoryRouter()
