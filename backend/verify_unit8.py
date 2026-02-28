import os
import sys

# Add backend and root to sys.path
backend_path = r"e:\Drive\Antigravitiy\Orchesta assistant\05_Mimi_HomeTutor"
if backend_path not in sys.path:
    sys.path.append(backend_path)

from core.agents.policy_agent import KnowledgeAgent

agent = KnowledgeAgent()
query = "Science Unit 8 học những vấn đề gì"
print(f"--- TESTING QUERY: {query} ---")

# Manually run the search logic to see scores
query_words = set(query.lower().split())
stop_words = {"môn", "có", "những", "nào", "là", "của", "và", "trong", "cho", "với"}
query_words = query_words - stop_words
print(f"Query words: {query_words}")

for skill_id, skill in agent.store.skills.items():
    target_text = (skill.get('title', '') + " " + skill.get('logic_summary', '')).lower()
    # Simple regex-like splitting to catch more words
    import re
    target_words = set(re.findall(r'\w+', target_text))
    keyword_overlap = len(query_words.intersection(target_words))
    keyword_score = keyword_overlap / max(1, len(query_words))
    
    total_score = (0 * 0.7) + (keyword_score * 0.3) # Assuming no embeddings
    if "unit8" in skill_id or "unit_8" in skill_id or keyword_overlap > 0:
        print(f" Skill: {skill_id} | Overlap: {keyword_overlap} | Score: {total_score:.4f}")

results = agent.store.search_skills(query)
print(f"\nFinal results found: {len(results)}")

# Trigger rule-based response check
print("\n--- RULE-BASED RESPONSE CHECK ---")
from core.agents.scholar_agent import ScholarAgent
scholar = ScholarAgent()
# Construct a context string from results
context = "\n".join([r.get('logic_summary', '') for r in results])
response = scholar._get_rule_based_response(query, context)
print(f"Mimi's Fallback Response: {response}")
