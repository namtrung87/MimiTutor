import os
import sys

# Add backend and root to sys.path
backend_path = r"e:\Drive\Antigravitiy\Orchesta assistant\05_Mimi_HomeTutor"
if backend_path not in sys.path:
    sys.path.append(backend_path)

from core.agents.policy_agent import KnowledgeAgent
from core.document_loader import DocumentLoader

print("--- DIAGNOSTIC SYNC ---")
agent = KnowledgeAgent()
print(f"Path to search: {agent.mimi_learning_path}")
print(f"Exists? {os.path.exists(agent.mimi_learning_path)}")

loader = DocumentLoader(knowledge_base_path=agent.mimi_learning_path)
docs = loader.load_documents()
print(f"Found {len(docs)} documents.")
for d in docs:
    print(f" - {d['filename']} ({len(d['content'])} chars)")

print("\nStarting Agent Sync...")
count = agent.sync_mimi_learning()
print(f"Agent reported {count} segments synced.")

# Check for the store file
store_path = os.path.join(backend_path, "chroma_knowledgedb", "skills_store.json")
print(f"Store exists at {store_path}? {os.path.exists(store_path)}")
