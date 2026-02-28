import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Late imports to avoid issues while package installs
# from llama_index.core import PropertyGraphIndex, StorageContext, Document
# from llama_index.vector_stores.lancedb import LanceDBVectorStore

class HybridStore:
    """
    Handles dual-layer indexing:
    1. Vector Search (LanceDB): Fast semantic retrieval.
    2. Property Graph (LlamaIndex): Structured entity and relationship reasoning.
    """
    def __init__(self, db_path: str = "data/hybrid_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.graph_index = None
        self.vector_store = None
        self._initialized = False

    def _lazy_init(self):
        if self._initialized:
            return
        
        try:
            import lancedb
            from llama_index.core import StorageContext, PropertyGraphIndex
            from llama_index.vector_stores.lancedb import LanceDBVectorStore
            from llama_index.embeddings.gemini import GeminiEmbedding
            from llama_index.llms.gemini import Gemini
            
            # Setup Models
            embed_model = GeminiEmbedding(model_name="models/text-embedding-004")
            llm = Gemini(model_name="models/gemini-1.5-flash-latest")
            
            # Setup Vector Store
            self.vector_store = LanceDBVectorStore(
                uri=str(self.db_path / "lancedb"), 
                table_name="chunks"
            )
            
            # Setup Storage Context
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Note: For PropertyGraph, we typically need a graph store like Neo4j.
            # Here we use the default (SimplePropertyGraphStore) which is local/json.
            self.graph_index = PropertyGraphIndex.from_documents(
                [],
                storage_context=storage_context,
                embed_model=embed_model,
                llm=llm,
                show_progress=True
            )
            
            self._initialized = True
            print("HybridStore initialized successfully.")
        except ImportError as e:
            print(f"HybridStore initialization failed (missing packages): {e}")
        except Exception as e:
            print(f"HybridStore error: {e}")

    def add_documents(self, chunks: List[Dict[str, Any]]):
        """
        Adds chunks to both Vector and Graph stores.
        """
        self._lazy_init()
        if not self.graph_index:
            print("Cannot add documents: Store not initialized.")
            return

        from llama_index.core import Document
        
        docs = []
        for chunk in chunks:
            doc = Document(
                text=chunk["text"],
                metadata={
                    "parent_title": chunk.get("parent_title", "N/A"),
                    "type": chunk.get("type", "semantic")
                }
            )
            docs.append(doc)
            
        # This will update both Vector Store and Property Graph
        for doc in docs:
            self.graph_index.insert(doc)
        
        print(f"Indexed {len(docs)} documents into Hybrid Store.")

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs a hybrid search.
        """
        self._lazy_init()
        if not self.graph_index:
            return []

        # LlamaIndex PropertyGraphIndex retriever handles both graph and vector search
        retriever = self.graph_index.as_retriever(
            include_text=True,
            similarity_top_k=limit
        )
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.text,
                "score": getattr(node, "score", 0),
                "metadata": node.metadata
            })
        return results

if __name__ == "__main__":
    # Example usage
    store = HybridStore()
    # store.add_documents([{"text": "Hello world", "parent_title": "Test"}])
    # print(store.search("hello"))
