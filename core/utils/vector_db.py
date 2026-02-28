import os
import chromadb
from typing import List, Dict, Any, Optional
from core.utils.llm_manager import LLMManager

class VectorMemory:
    """
    Handles session-based memory using ChromaDB.
    """
    def __init__(self, collection_name: str = "orchesta_memory"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.llm = LLMManager()

    def add_memory(self, text: str, metadata: Dict[str, Any], doc_id: str):
        embedding = self.llm.embed(text)
        if embedding:
            self.collection.add(
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text],
                ids=[doc_id]
            )

    def query_memory(self, query_text: str, n_results: int = 3) -> List[str]:
        embedding = self.llm.embed(query_text)
        if not embedding: return []
        
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        return results['documents'][0] if results['documents'] else []
