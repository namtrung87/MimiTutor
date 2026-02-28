import os
import sys

# Add backend and root to sys.path
backend_path = r"e:\Drive\Antigravitiy\Orchesta assistant\05_Mimi_HomeTutor"
if backend_path not in sys.path:
    sys.path.append(backend_path)

from core.agents.policy_agent import KnowledgeAgent

agent = KnowledgeAgent()
query = "Science Unit 8"
print(f"--- TESTING QUERY: {query} ---")

# Step 1: Check retrieval
results = agent.store.search_skills(query)
print(f"Found {len(results)} results.")
for r in results:
    print(f" - Title: {r['title']} | Score: N/A")

# Step 2: Check context building
context = "\n\n".join([f"Source ({r['title']}):\n{r['logic_summary'][:1000]}" for r in results])
print("\n--- GENERATED CONTEXT ---")
print(context)

# Step 3: Check ScholarAgent selection
from core.agents.scholar_agent import ScholarAgent
scholar = ScholarAgent()
response = scholar._get_rule_based_response(query, context)
print("\n--- SCHOLAR RESPONSE ---")
print(response)
