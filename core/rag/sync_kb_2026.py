import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

from core.rag.ingestion_manager import IngestionManager
from core.rag.hybrid_store import HybridStore

def main():
    print("🚀 --- Starting 2026 Hybrid RAG Sync (Mimi Learning) ---")
    
    # Paths
    # Root dir of assistant is e:\Drive\Antigravitiy\Orchesta assistant
    # Mimi learning is at e:\Drive\Antigravitiy\Mimi learning
    mimi_dir = Path(root_dir).parent / "Mimi learning"
    target_pdf = mimi_dir / "Science_Adventure_Unit8.md"
    
    if not target_pdf.exists():
        print(f"❌ Error: Target file not found at {target_pdf}")
        return

    # 1. Ingestion
    ingestor = IngestionManager(metadata_path=str(root_dir / "data" / "rag_metadata_2026.json"))
    print(f"📦 Processing: {target_pdf.name}...")
    
    # Process the file (Parsing + Chunking)
    # Force=True because previous runs might have failed gracefully due to missing docling
    processing_result = ingestor.process_file(str(target_pdf), force=True)
    
    if not processing_result:
        print("✅ Document already up-to-date in metadata.")
        return

    # 2. Hybrid Indexing
    print(f"🔍 Indexing {len(processing_result['chunks'])} chunks into Hybrid Store...")
    store = HybridStore(db_path=str(root_dir / "data" / "hybrid_db_2026"))
    store.add_documents(processing_result['chunks'])
    
    # 3. Test Search
    query = "What are the components of a cell?"
    print(f"\n🧪 Testing Hybrid Search for: '{query}'")
    results = store.search(query, limit=3)
    
    print(f"Found {len(results)} results:")
    for i, res in enumerate(results):
        print(f"--- Result {i+1} ---")
        print(f"Title: {res['metadata'].get('parent_title', 'N/A')}")
        print(f"Text: {res['text'][:300]}...")
        print("-" * 20)

    print("\n✅ 2026 RAG Sync Complete!")

if __name__ == "__main__":
    main()
