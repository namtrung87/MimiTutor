from core.agents.policy_agent import KnowledgeAgent
from core.state import AgentState
import os

class ScholarAgent(KnowledgeAgent):
    """
    ScholarAgent: Specialized pedagogical agent for ACCA/CFA/Finance.
    Integrates Socratic tutoring with advanced RAG and roadmap awareness.
    """
    def __init__(self):
        super().__init__()
        self.system_prompt = self._load_scholar_prompt()

    def _load_scholar_prompt(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "../../prompts", "scholar_system.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are a Science Tutor. Do not mention missing files."

    def process_request(self, state: AgentState) -> dict:
        """
        Main pedagogical loop.
        """
        messages = state.get("messages", [])
        user_input = ""
        for msg in reversed(messages):
            if msg and isinstance(msg, str) and not msg.startswith("System"):
                user_input = msg
                break
        
        if not user_input:
            user_input = messages[-1] if messages else ""
            
        user_input_clean = user_input.replace("Mimi: ", "").replace("Parent: ", "").strip()
        
        # 1. Retrieve deep context (RAG)
        results = self.store.search_skills(user_input_clean)
        context_str = ""
        if results:
            context_str = "\n".join([f"Source ({r['title']}): {r['logic_summary']}" for r in results])
        
        # 2. Enhanced Prompting with Memory and Feedback
        critic_feedback = state.get("critic_feedback")
        feedback_section = f"\n--- CRITIC FEEDBACK (ADJUST RESPONSE) ---\n{critic_feedback}\n" if critic_feedback else ""
        
        full_prompt = f"""
        {self.system_prompt}
        
        {feedback_section}
        
        --- STUDY MATERIAL CONTEXT (RAG) ---
        {context_str if context_str else "No specific study material found."}
        
        --- LONG-TERM MEMORY (PROGRESS) ---
        {state.get('long_term_memory', 'None.')}
        
        --- STUDENT REQUEST ---
        {user_input}
        """
        
        # 3. LLM Query
        response = self.researcher.query(full_prompt, complexity="L3")
        
        if not response or response == "FALLBACK_TRIGGERED":
            print(f"  [ScholarAgent] LLM Failed. Using rule-based fallback.")
            response = self._get_rule_based_response(user_input_clean, context_str)
            
        return {"messages": [f"Scholar Agent: {response}"]}

    def _get_rule_based_response(self, user_input, context):
        """Offline fallback that provides direct info if available."""
        if not context:
            return f"Chào em! Anh/Chị đang sắp xếp lại tài liệu học tập một chút. Em muốn hỏi về Science Unit 8 hay chủ đề nào trong sách Khoa học lớp 7 nhỉ?"
        
        # Heuristic: try to find a relevant sentence
        input_lower = user_input.lower()
        sentences = [s.strip() for s in context.split(".") if len(s.strip()) > 30]
        match = None
        for s in sentences:
            if any(w in s.lower() for w in input_lower.split()):
                match = s
                break
        
        if not match and sentences:
            match = sentences[0]
            
        if match:
            return f"Chào Mimi! Về '{user_input}', anh/chị tìm thấy thông tin này trong tài liệu: \"{match}\". Hy vọng nó giúp ích cho em! Em có muốn anh/chị giải thích thêm không?"
        
        return "Chào Mimi! Hiện tại anh/chị đang truy cập tài liệu offline. Em thử hỏi chi tiết hơn về một khái niệm trong Science Unit 8 xem sao?"

def scholar_agent_node(state: AgentState):
    agent = ScholarAgent()
    return agent.process_request(state)
