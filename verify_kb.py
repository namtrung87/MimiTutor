import os
from core.agents.policy_agent import KnowledgeAgent

def verify_search():
    print("🚀 Verifying Knowledge Base search for Mimi Science...")
    agent = KnowledgeAgent()
    
    queries = [
        "Unit 9 Electricity current",
        "What is a conductor?",
        "How to measure current?"
    ]
    
    for query in queries:
        print(f"\n🔍 Searching for: {query}")
        results = agent.store.search_skills(query)
        print(f"✅ Found {len(results)} results.")
        for r in results:
            print(f"- Title: {r.get('title')}")
            print(f"  Summary: {r.get('logic_summary')[:200]}...")

if __name__ == "__main__":
    verify_search()
