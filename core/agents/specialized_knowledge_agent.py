import os
from typing import List, Dict, Any, Optional
from core.agents.base_agent import BaseAgent
from core.state import AgentState
from core.vector_store_chroma import ChromaSkillStore
from core.vector_store_kinh_dich import ChromaKinhDichStore
from core.utils.bot_logger import get_logger

logger = get_logger("specialized_knowledge_agent")

class SpecializedKnowledgeAgent(BaseAgent):
    """
    Unified agent for all specialized knowledge domains.
    Handles academic, research, legal, and philosophical queries.
    """
    def __init__(self, role: str = "academic"):
        # Map roles to prompt files
        role_prompt_map = {
            "research": "research_scholarship_lead",
            "bank": "shadow_bank_consultant",
            "tech": "creative_tech_skill_architect",
            "growth": "growth_branding_specialist",
            "academic": "academic_success_assistant",
            "advisor": "strategic_advisory_consultant",
            "legal": "han_media_legal_guardian",
            "mimi": "mimi_socratic",
            "cos": "executive_chief_of_staff",
            "heritage": "heritage_philosophy_scholar",
            "wellness": "wellness_performance_coach",
            "learning": "personal_intellectual_tutor",
            "iching": "iching_system",
            "scholar": "scholar_system"
        }
        
        prompt_file = role_prompt_map.get(role, "academic_success_assistant")
        super().__init__(name=f"{role.capitalize()}Agent", prompt_file=prompt_file)
        self.role = role
        
        # Load appropriate vector store
        if role == "iching":
            self.store = ChromaKinhDichStore()
        else:
            self.store = ChromaSkillStore(persist_directory="chroma_knowledgedb")

    def _detect_subject(self, text: str) -> str:
        text = text.lower()
        if any(w in text for w in ["toán", "math", "số", "cộng", "trừ"]): return "Math"
        if any(w in text for w in ["science", "khoa học", "vật lý", "hóa học", "sinh học"]): return "Science"
        if any(w in text for w in ["văn", "literature", "tiếng việt"]): return "Literature"
        return "English" # Default

    def get_context(self, question: str) -> str:
        """Retrieves context from the appropriate vector store."""
        if self.role == "iching":
            results = self.store.search(question, n_results=5)
            return "\n".join([f"Source: {r['metadata'].get('title')} - {r['content']}" for r in results])
        else:
            results = self.store.search_skills(question)
            return "\n".join([f"Source: {r['title']} - {r['logic_summary']}" for r in results])

    def process_request(self, state: AgentState) -> Dict[str, Any]:
        """Main execution logic for the specialized agent."""
        user_input = self.extract_last_message(state["messages"])
        context = self.get_context(user_input)
        
        memory_str = "\n".join(state.get("long_term_memory", []))
        
        full_prompt = f"""
        {self._system_prompt}
        
        --- LONG-TERM MEMORY (USER PROFILE) ---
        {memory_str if memory_str else "None."}

        --- CONTEXT FROM KNOWLEDGE BASE ---
        {context if context else 'No local document found.'}
        
        USER QUESTION: {user_input}
        """
        
        response = self.query(full_prompt, complexity="L3")

        # Ported from SocraticAgent: Update Learning Tracker
        if self.role in ["mimi", "scholar"]:
            try:
                from core.services.mimi_learning_tracker import learning_tracker
                subject = self._detect_subject(user_input)
                # If the response ends with a question, it's a progress point (+2)
                mastery = 2 if "?" in response else 0
                learning_tracker.log_session(subject, user_input[:50], response[:100], mastery)
            except Exception as e:
                logger.error(f"  [SpecializedKnowledgeAgent] Learning tracker failed: {e}")

        return {"messages": [f"{self.name}: {response}"]}

def specialized_knowledge_node(state: AgentState):
    role = state.get("routing_category", "academic")
    agent = SpecializedKnowledgeAgent(role=role)
    return agent.process_request(state)
