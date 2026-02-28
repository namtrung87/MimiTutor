import os
import uuid
import json
from datetime import datetime

# ChromaDB currently has compatibility issues with Pydantic V1 on Python 3.14.
# Using JSON fallback as the primary mechanism for stability.
CHROMA_AVAILABLE = False

class PriorityMemory:
    def __init__(self, persist_directory=None):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.data_dir = os.path.join(root_dir, "data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.fallback_path = os.path.join(self.data_dir, "mimi_priority_fallback.json")
        self.use_fallback = True # Force fallback for Python 3.14 stability
        print("  [PriorityMemory] Using JSON fallback mode (Python 3.14 compatible).")

    def add_golden_answer(self, question: str, answer: str, metadata: dict = None):
        """
        Adds a fine-tuned Question-Answer pair to the priority memory.
        """
        self._add_to_json(question, answer, metadata)

    def find_priority_answer(self, question: str, threshold: float = 0.9) -> str:
        """
        Searches for a highly similar question in the priority database.
        Returns the answer if found. (Threshold ignored in JSON exact match mode).
        """
        return self._find_in_json(question)

    def _add_to_json(self, question: str, answer: str, metadata: dict):
        data = []
        if os.path.exists(self.fallback_path):
            with open(self.fallback_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    print(f"  [PriorityMemory] Error loading JSON: {e}")
                    pass
        
        data.append({
            "question": question,
            "answer": answer,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(self.fallback_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [PriorityMemory] Saved to JSON: {question[:50]}...")

    def _find_in_json(self, question: str) -> str:
        if not os.path.exists(self.fallback_path):
            return None
            
        with open(self.fallback_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"  [PriorityMemory] Search error: {e}")
                return None
            
        q_lower = question.lower().strip()
        # Search for exact match (or simple string overlap for basic priority)
        for item in reversed(data):
            if item["question"].lower().strip() == q_lower:
                print(f"  [PriorityMemory] Priority match found (JSON) -> {item['answer'][:50]}...")
                return item["answer"]
        return None

# Singleton instance
priority_memory = PriorityMemory()
