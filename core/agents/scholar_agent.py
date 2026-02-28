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
        all_results = self.store.search_skills(user_input_clean)
        # Filter strictly for Mimi Science content to avoid cross-module leakage
        results = [r for r in all_results if r.get('title', '').startswith("Mimi Science:")]
        
        context_str = self._build_context(results)
        
        # 2. Enhanced Prompting with Memory and Feedback
        critic_feedback = state.get("critic_feedback")
        feedback_section = f"\n--- CRITIC FEEDBACK (ADJUST RESPONSE) ---\n{critic_feedback}\n" if critic_feedback else ""
        
        # 3. Build teaching prompt - instruct Mimi to USE the content, not cite the source
        context_instruction = ""
        if context_str:
            context_instruction = f"""
--- TÀI LIỆU THAM KHẢO (dùng để giảng giải, không liệt kê tên tài liệu ra) ---
{context_str}
Hãy tự nhiên lồng ghép kiến thức từ tài liệu vào lời giải thích của bạn. 
Đừng nói "Trong tài liệu..." hay "Nguồn:...". Hãy giải thích như một người thầy thực sự biết kiến thức đó.
"""
        else:
            context_instruction = "\n--- Không có tài liệu tham khảo. Hãy dùng kiến thức nền của bạn để giảng giải. ---\n"
        
        full_prompt = f"""
        {self.system_prompt}
        
        {feedback_section}
        
        {context_instruction}
        
        --- HỒ SƠ HỌC TẬP (lịch sử bộ nhớ dài hạn) ---
        {state.get('long_term_memory', 'Chưa có dữ liệu.')}
        
        --- CÂU HỎI CỦA HỌC SINH ---
        {user_input}
        """
        
        # 3. LLM Query
        response = self.researcher.query(full_prompt, complexity="L3")
        
        if not response or response == "FALLBACK_TRIGGERED" or str(response).strip().lower() == "none":
            print(f"  [ScholarAgent] LLM Failed or returned None. Using rule-based fallback.")
            response = self._get_rule_based_response(user_input_clean, context_str)
            
        return {
            "messages": [f"Scholar Agent: {response}"],
            "final_response": response
        }

    def _get_rule_based_response(self, user_input, context):
        """Offline fallback that provides a warm, teacher-style answer if available."""
        import random
        input_lower = user_input.lower().strip()
        
        # 1. Warm Greeting Handling
        greetings = [
            "chao", "chào", "hi", "hello", "xin chao", "xin chào", "hey", "chao chi", "chào chị", 
            "chao mimi", "chào mimi", "alo", "mimi oi", "mimi ơi"
        ]
        if any(g in input_lower for g in greetings) and len(input_lower) < 25:
            openings = [
                "Chào Mimi thân yêu! ✨ Chị đã sẵn sàng đồng hành cùng em rồi đây.",
                "Chào em nhé! 🌟 Hôm nay em muốn chị em mình cùng khám phá bài học nào nhỉ?",
                "Chào Mimi! ✨ Rất vui được gặp lại em. Chúng mình bắt đầu buổi học nhé?"
            ]
            return random.choice(openings)

        if not context:
            return (
                f"Câu hỏi hay lắm! 🌟 Chị đang cố gắng tìm tài liệu liên quan đến chủ đề này nhưng "
                f"chưa có ngay bây giờ. Em có thể hỏi cụ thể hơn về một khái niệm trong bài học không? "
                f"Ví dụ, chủ đề này có phần nào em thấy khó hiểu nhất?"
            )
        
        # 2. Score sentences with Source-awareness
        import re
        query_unit_match = re.search(r'unit\s*(\d+)', input_lower)
        target_unit = query_unit_match.group(1) if query_unit_match else None
        
        scored = []
        current_source_unit = None
        
        lines = context.split("\n")
        for line in lines:
            line_clean = line.strip()
            if not line_clean: continue
            
            if line_clean.startswith("Source ("):
                unit_match = re.search(r'unit\s*(\d+)', line_clean.lower())
                current_source_unit = unit_match.group(1) if unit_match else None
                continue
            
            s = line_clean.replace("- ", "").replace("*", "").strip()
            if len(s) < 25: continue
            
            blocklist = ["generated based on", "notebooklm", "visual:", "speaker notes:"]
            if any(b in s.lower() for b in blocklist):
                continue
                
            s_low = s.lower()
            words = set(ui_word for ui_word in input_lower.replace("?", "").split() if len(ui_word) >= 3)
            overlap = sum(2 for word in words if word in s_low)
            
            if target_unit and current_source_unit == target_unit:
                overlap += 30
            
            boost = 0
            if any(kw in s_low for kw in [" là ", " là sự ", " được gọi là ", " gồm ", " definition "]):
                boost += 10
            if " ví dụ " in s_low or " example " in s_low:
                boost += 5
                
            instructional_terms = ["upload", "click", "file", "notebook", "made for you", "link"]
            if any(term in s_low for term in instructional_terms):
                boost -= 20
            
            if line_clean.startswith("#") or s.endswith(":") or len(s) < 40:
                boost -= 5

            score = overlap + boost
            if score > 5:
                # Store cleaned sentence
                s_clean = s.replace("#", "").replace("**", "").replace("__", "").replace("`", "").strip()
                # Handle Term: Definition patterns
                if len(s_clean) < 50 and ":" in s_clean:
                    s_clean = s_clean.split(":", 1)[-1].strip()
                scored.append((score, s_clean))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored:
            # Pick top 1-2 sentences to provide a richer answer
            top_results = []
            seen = set()
            for score, content in scored[:2]:
                if content not in seen:
                    top_results.append(content)
                    seen.add(content)
            
            final_content = " ".join(top_results)
            
            # Dynamic Openings
            templates = [
                f"Về chủ đề này, chị biết một điều rất thú vị nhé: {final_content}",
                f"Đây là một phần rất quan trọng nè em: {final_content}",
                f"Ồ, câu hỏi của em hay quá! Để chị giải thích nhé: {final_content}",
                f"Chị hiểu ý em rồi! Trong bài học, chúng ta có kiến thức này nè: {final_content}"
            ]
            
            response = random.choice(templates)
            suffix = " Em thấy phần này có chỗ nào chưa rõ không? Cứ hỏi chị để chị giải thích kỹ hơn nhé! ✨"
            return response + suffix
        
        # 3. Final Fallback if no specific context matched
        return (
            "Chị đang tìm thêm thông tin để giải thích cho em dễ hiểu nhất. "
            "Trong lúc chờ đợi, em có muốn chị em mình ôn lại phần nào khác không?"
        )
        
def scholar_agent_node(state: AgentState):
    agent = ScholarAgent()
    return agent.process_request(state)
