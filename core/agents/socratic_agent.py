from core.agents.policy_agent import KnowledgeAgent
from core.state import AgentState
import os

class SocraticAgent(KnowledgeAgent):
    """
    Specialized Agent for Mimi that uses the Socratic method.
    Inherits from KnowledgeAgent to leverage RAG capabilities.
    """
    def __init__(self):
        super().__init__()
        self.system_prompt = self._load_socratic_prompt()

    def _load_socratic_prompt(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "../../prompts", "mimi_socratic.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "You are a Socratic Science Tutor. Do not mention missing files."

    def socratic_node(self, state: AgentState):
        """
        Processes the user message and returns a Socratic response for exercises/problems.
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
        
        # 1. Retrieve relevant context from study materials
        results = self.store.search_skills(user_input_clean)
        context_str = ""
        sources = []
        if results:
            context_str = "\n".join([f"Source ({r['title']}): {r['logic_summary']}" for r in results])
            sources = [r['title'] for r in results]
        
        print(f"  [SocraticAgent] Fixed Mode: EXERCISE")

        # Load teacher feedback
        teacher_feedback = self._load_teacher_feedback()
        critic_feedback = state.get("critic_feedback")
        feedback_section = f"\n--- CRITIC FEEDBACK (REVISE YOUR PREVIOUS RESPONSE) ---\n{critic_feedback}\n" if critic_feedback else ""

        # Filter memory and extract learning profile
        raw_memory = state.get('long_term_memory', [])
        clean_memory = []
        learning_profile = "None."
        
        if isinstance(raw_memory, list):
            for m in raw_memory:
                if "[LEARNING_PROFILE]" in str(m):
                    learning_profile = str(m)
                elif "readiness" not in str(m).lower() and "tension" not in str(m).lower():
                    clean_memory.append(m)
        else:
            clean_memory = str(raw_memory)
            
        memory_str = "\n".join([f"- {m}" for m in clean_memory]) if isinstance(clean_memory, list) else clean_memory
        
        # Filter history
        history = [m for m in state['messages'][:-1] if isinstance(m, str) and not m.startswith("System:")]
        
        full_prompt = f"""
        {self.system_prompt}
        
        --- TASK: SCIENCE TUTOR (STAGE 7) ---
        Use THE SOCRATIC METHOD. Break down the problem, provide hints. DO NOT give the answer.
        
        CRITICAL RULE: STICK EXCLUSIVELY TO THE CAMBRIDGE LOWER SECONDARY SCIENCE STAGE 7 CURRICULUM.
        Do not confuse with other levels. Use the provided context from the knowledge base as your primary source of truth.
        
        {feedback_section}
        
        --- STUDENT LEARNING PROFILE ---
        {learning_profile}
        
        PEDAGOGICAL INSTRUCTION:
        1. Check "Mastered Topics" and use them as analogies to explain new concepts.
        2. Check "Struggled Topics" and provide extra scaffolding/patience when these arise.
        3. If "Poor Responses" are noted, simplify your language and be more encouraging.
        
        --- TEACHER FEEDBACK ON STUDENT ---
        {teacher_feedback}
        
        --- STUDY MATERIAL CONTEXT (CAMBRIDGE SCIENCE 7) ---
        {context_str if context_str else "Sử dụng kiến thức chuẩn về chương trình Cambridge Science Stage 7 để giải thích."}
        
        --- RELEVANT PAST CONTEXT ---
        {memory_str if memory_str else 'None.'}

        --- CHAT HISTORY ---
        {history}
        
        STUDENT: {user_input_clean}
        
        CRITICAL FINAL INSTRUCTION: USE THE SOCRATIC METHOD. END YOUR RESPONSE WITH A SINGLE GUIDING QUESTION.
        RESPOND AS FRIENDLY OLDER SIBLING (SOCRATIC TUTOR):
        """
        
        response = self.researcher.query(full_prompt, complexity="L3")
        
        if response == "FALLBACK_TRIGGERED":
            response = self._get_rule_based_socratic_response(user_input_clean, context_str)
        
        # Log the interaction
        self._log_interaction(user_input_clean, response)
        
        return {"messages": [f"Mimi Agent: {response}"]}

    def _get_rule_based_response(self, user_input, context, mode, sources):
        """
        Hyper-upgraded Logic (Offline Mode).
        Bifurcates based on detected mode to provide specialized fallback.
        """
        if mode == "CONTENT_INQUIRY" and context:
            source_info = f"\n\n> [!NOTE]\n> **Trích dẫn từ**: {sources[0] if sources else 'Tài liệu học tập'}"
            
            # Extract a meaningful snippet (heuristic: look for paragraphs or long sentences)
            paragraphs = [p.strip() for p in context.split("\n") if len(p.strip()) > 50]
            if not paragraphs:
                paragraphs = [s.strip() for s in context.split(".") if len(s.strip()) > 40]
            
            summary = paragraphs[0] if paragraphs else context[:500]
            
            return f"Chào Mimi! Về câu hỏi này, anh/chị tìm thấy thông tin quan trọng trong sách của em nè:\n\n\"{summary}\"\n\nĐoạn này giải thích khá rõ về {user_input}. Em đọc qua thấy có chỗ nào khó hiểu không?{source_info}"
            
        return self._get_rule_based_socratic_response(user_input, context)

    def _get_rule_based_socratic_response(self, user_input, context):
        """
        Hyper-upgraded Socratic Logic (Offline Mode).
        Provides specific, structured guidance based on RAG context.
        """
        input_lower = user_input.lower().strip()
        
        # 1. Immediate Intent Discovery
        if any(w in input_lower for w in ["chào", "hi", "hello"]):
            return "Chào Mimi! Hôm nay em muốn cùng anh/chị khám phá bài học nào đây? Science Unit 8 hay là phần nào khác nhỉ?"
            
        if any(w in input_lower for w in ["không biết", "ko biết", "don't know", "i don't know"]):
            if context:
                important_terms = self._extract_important_terms(context)
                if important_terms:
                    return f"Đừng lo nhé! Trong bài học này có nhắc đến **{important_terms[0]}**. Em thử nhớ lại xem khái niệm này có giúp mình giải quyết vấn đề không? Cứ bình tĩnh suy nghĩ nhé!"
            return "Đừng lo! Chúng mình chia nhỏ ra nhé. Em thấy phần nào là khó hiểu nhất trong câu hỏi này?"

        # 2. Contextual Deep Dive
        if context:
            # Look for specific scientific relationships
            if "physical change" in input_lower or "thay đổi vật lý" in input_lower:
                return "Câu hỏi về thay đổi vật lý rất hay! Em thử nghĩ xem: sau khi thay đổi, chúng mình có thể biến nó quay lại như cũ không (như đá tan thành nước ấy)? Ý em thế nào?"
            
            if "chemical change" in input_lower or "thay đổi hóa học" in input_lower:
                return "Trong tài liệu có nói về thay đổi hóa học tạo ra 'chất mới'. Theo em, làm sao để mình biết là đã có một 'chất mới' xuất hiện nhỉ? Có dấu hiệu gì như bọt khí hay đổi màu không?"

            if "acid" in input_lower or "alkali" in input_lower:
                return "À, về Acid và Alkali! Em có nhớ Team Acid và Team Alkali thường 'đánh nhau' hay 'hòa giải' để thành muối và nước không? Thử xem bảng pH xem chúng ở đâu nhé!"

            # Dynamic hint extraction
            sentences = [s.strip() for s in context.split(".") if len(s) > 10]
            if len(sentences) > 1:
                import random
                hint_sentence = random.choice(sentences[:3])
                return f"Anh/Chị vừa đọc được một ý trong bài: \"{hint_sentence}\". Em thấy ý này có liên quan gì đến điều em đang thắc mắc không? Giải thích cho anh/chị nghe với!"

        # 3. Last Resort - Interactive Nudges
        prompts = [
            f"Câu hỏi về '{user_input}' thực sự rất thú vị! Em thử đoán xem bước tiếp theo sẽ là gì?",
            "Anh/Chị muốn nghe suy nghĩ của em trước. Em cứ nói đại đi, sai cũng không sao, mình cùng sửa mà!",
            f"Nếu em là một nhà thám hiểm đang tìm hiểu về {user_input if len(user_input) < 20 else 'vấn đề này'}, em sẽ làm gì đầu tiên?",
            "Hôm nay chúng mình đã học được nhiều điều rồi. Em thử tóm tắt lại ý quan trọng nhất theo cách của em xem sao?"
        ]
        import random
        return random.choice(prompts)

    def _extract_important_terms(self, context):
        keywords = ["Physical change", "Chemical change", "Acid", "Alkali", "Neutralization", "pH Scale", "Hydrogen", "Carbon Dioxide", "Salt", "Water"]
        return [k for k in keywords if k.lower() in context.lower()]

    def _load_teacher_feedback(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        feedback_dir = os.path.join(root_dir, "05_Mimi_HomeTutor", "teacher_feedback")
        content = []
        if os.path.exists(feedback_dir):
            for f in os.listdir(feedback_dir):
                if f.endswith((".txt", ".md")):
                    with open(os.path.join(feedback_dir, f), 'r', encoding='utf-8') as file:
                        content.append(file.read())
        return "\n".join(content) if content else "No specific teacher feedback available."

    def _log_interaction(self, user_msg, bot_msg):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        log_dir = os.path.join(root_dir, "05_Mimi_HomeTutor", "chat_history")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        import json
        from datetime import datetime
        log_file = os.path.join(log_dir, f"session_{datetime.now().strftime('%Y%m%d')}.jsonl")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "user": user_msg,
                "bot": bot_msg
            }, ensure_ascii=False) + "\n")

def socratic_agent_node(state: AgentState):
    agent = SocraticAgent()
    return agent.socratic_node(state)
