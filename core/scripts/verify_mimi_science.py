import sys
import os

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.agents.policy_agent import KnowledgeAgent

def verify_sync():
    print("--- Starting Mimi Science Sync Verification ---")
    agent = KnowledgeAgent()
    
    # 1. Trigger sync
    count = agent.sync_mimi_learning()
    print(f"Ingested {count} documents.")
    
    # 2. Check store content
    if hasattr(agent.store, 'skills'):
        print(f"DEBUG: All store keys: {list(agent.store.skills.keys())}")
        # ChromaSkillStore converts titles to lowercase/underscores
        mimi_entries = [k for k in agent.store.skills.keys() if "mimi_science" in k]
        print(f"Found {len(mimi_entries)} science entries: {mimi_entries}")
        
        # Check for non-science (old) entries
        old_entries = [k for k in agent.store.skills.keys() if k.startswith("mimi_learning_")]
        if old_entries:
            print(f"FAILED: Found {len(old_entries)} old entries that should have been cleared: {old_entries}")
        else:
            print("SUCCESS: Old entries cleared.")
            
        if any("science" in k for k in mimi_entries):
            print("SUCCESS: Science PDF correctly ingested.")
        else:
            print("FAILED: Science PDF NOT found in store.")
            
if __name__ == "__main__":
    verify_sync()
