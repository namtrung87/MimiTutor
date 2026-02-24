import os
import json
from core.state import AgentState
from core.utils.llm_manager import LLMManager

class SkillExtractorAgent:
    """
    Agent responsible for extracting reusable skills and patterns from successful interactions.
    """
    def __init__(self):
        self.llm = LLMManager()
        self.skills_dir = os.path.join(os.getcwd(), "skills", "extracted")
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)

    def extract_skill(self, state: AgentState) -> dict:
        """
        Analyzes the last successful interaction to extract a reusable skill pattern.
        """
        messages = state.get("messages", [])
        if not messages:
            return {"status": "no_messages"}

        # For simplicity, we assume the last message contains a successful task completion
        last_context = messages[-3:] if len(messages) >= 3 else messages
        
        prompt = f"""
        Bạn là chuyên gia trích xuất kỹ năng (Skill Extractor AI).
        
        NGỮ CẢNH TƯƠNG TÁC GẦN ĐÂY:
        {json.dumps(last_context, indent=2)}
        
        NHIỆM VỤ:
        1. Xác định xem có quy trình, thuật toán hoặc mẫu kiến thức nào mới vừa được giải quyết hay không.
        2. Nếu có, hãy trích xuất nó thành một "Skill Definition" ngắn gọn dưới dạng Markdown.
        3. Định dạng gồm: Tên kỹ năng, Mô tả, Các bước thực hiện, và Ví dụ.
        
        Trả về kết quả dưới dạng Markdown. Nếu không có gì đáng trích xuất, trả về 'NONE'.
        """
        
        extraction = self.llm.query(prompt, complexity="L3")
        
        if "NONE" in extraction.upper():
            return {"status": "skipped", "reason": "No reusable pattern identified."}

        # Save to skills directory
        skill_id = extraction.split("\n")[0].replace("#", "").strip().lower().replace(" ", "_")
        file_path = os.path.join(self.skills_dir, f"{skill_id}.md")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(extraction)
            
        return {
            "status": "success",
            "skill_id": skill_id,
            "path": file_path
        }

def skill_extractor_node(state: AgentState):
    agent = SkillExtractorAgent()
    result = agent.extract_skill(state)
    return {
        "messages": [f"Skill Extractor: Đã trích xuất kỹ năng mới: {result.get('skill_id', 'N/A')}" if result["status"] == "success" else "Skill Extractor: Không tìm thấy mẫu kiến thức mới."],
        "extracted_skill": result
    }
