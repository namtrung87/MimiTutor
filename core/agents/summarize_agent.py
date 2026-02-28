from core.agents.policy_agent import KnowledgeAgent
from core.state import AgentState
import os

class SummarizeAgent(KnowledgeAgent):
    """
    Specialized Agent for Mimi that provides direct summaries of academic material.
    Inherits from KnowledgeAgent to leverage RAG capabilities.
    """
    def __init__(self):
        super().__init__()
        self.system_prompt = self._load_summarize_prompt()

    def _load_summarize_prompt(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        prompt_path = os.path.join(root_dir, "prompts", "mimi_summarize.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are an academic summarizer. Provide direct bulleted explanations."

    def summarize_node(self, state: AgentState):
        """
        Processes the user message and returns a concise summary.
        """
        messages = state.get("messages", [])
        user_input = ""
        for msg in reversed(messages):
            if msg and isinstance(msg, str) and not msg.startswith("System:"):
                user_input = msg
                break
        
        if not user_input:
            user_input = messages[-1] if messages else ""
            
        user_input_clean = user_input.replace("Mimi: ", "").replace("Parent: ", "").strip()
        
        # 1. Retrieve relevant context from study materials
        results = self.store.search_skills(user_input_clean)
        context_str = ""
        if results:
            context_str = "\n".join([f"Source ({r['title']}): {r['logic_summary']}" for r in results])
        
        # 2. Build Prompt
        history = [m for m in state['messages'][:-1] if isinstance(m, str) and not m.startswith("System:")]
        
        full_prompt = f"""
        {self.system_prompt}
        
        --- STUDY MATERIAL CONTEXT ---
        {context_str if context_str else "No specific study material found in database."}
        
        --- CHAT HISTORY ---
        {history}
        
        STUDENT: {user_input_clean}
        
        RESPOND AS FRIENDLY OLDER SIBLING (DIRECT TEACHING):
        """
        
        response = self.researcher.query_sync(full_prompt, complexity="L3")
        
        return {
            "messages": [f"Summarize Agent: {response}"],
            "final_response": response
        }

def summarize_agent_node(state: AgentState):
    agent = SummarizeAgent()
    return agent.summarize_node(state)
