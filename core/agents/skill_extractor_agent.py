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
        ltm = state.get("long_term_memory", [])
        last_context = messages[-5:] if len(messages) >= 5 else messages
        
        prompt = f"""
        Bạn là chuyên gia trích xuất kỹ năng (Skill Extractor AI).
        
        NGỮ CẢNH TƯƠNG TÁC GẦN ĐÂY:
        {json.dumps(last_context, indent=2)}
        
        LONG-TERM MEMORY RELEVANT:
        {json.dumps(ltm[:10], indent=2)}
        
        NHIỆM VỤ:
        1. Xác định xem có quy trình, kỹ thuật hoặc mẫu kiến thức nào đáng giá để tái sử dụng hay không.
        2. Chú trọng vào các kỹ thuật giải quyết lỗi (troubleshooting) hoặc quy trình tự động hóa.
        3. Nếu có, hãy trích xuất nó thành một "Skill Definition" Markdown.
        4. Định dạng gồm: Tên kỹ năng, Mô tả, Các bước thực hiện, và Ví dụ.
        
        Trả về kết quả dưới dạng Markdown. Nếu không có gì mới, trả về 'NONE'.
        """
        
        extraction = self.llm.query(prompt, complexity="L3")
        
        if "NONE" in extraction.upper() or len(extraction) < 50:
            return {"status": "skipped", "reason": "No reusable pattern identified."}

        # Save to skills directory
        skill_id = extraction.split("\n")[0].replace("#", "").strip().lower().replace(" ", "_").replace("*", "")
        file_path = os.path.join(self.skills_dir, f"{skill_id}.md")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(extraction)
            
        return {
            "status": "success",
            "skill_id": skill_id,
            "path": file_path
        }

    def proactive_scan(self, source_path: str = ".mock_memory.json") -> List[dict]:
        """
        Scans a memory or log file to extract skills without an active session.
        """
        results = []
        if not os.path.exists(source_path):
            return [{"status": "error", "reason": f"File {source_path} not found"}]

        with open(source_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                return [{"status": "error", "reason": f"Failed to parse JSON memory: {e}"}]

        # Sample or filter for high-value items (e.g., those with 'fix' or 'troubleshooting')
        high_value = [item for item in data if isinstance(item, dict) and any(kw in str(item).lower() for kw in ["fix", "troubleshoot", "error"])]
        
        for item in high_value[:5]: # Scan a few at a time
            dummy_state = {"messages": [item.get("text", "")], "long_term_memory": []}
            res = self.extract_skill(dummy_state)
            if res["status"] == "success":
                results.append(res)
        
        return results

def skill_extractor_node(state: AgentState):
    agent = SkillExtractorAgent()
    
    # Check if user explicitly asked for a scan
    user_input = state.get("messages", [""])[-1]
    if "proactive scan" in str(user_input).lower():
        results = agent.proactive_scan()
        return {
            "messages": [f"Skill Extractor: Proactive scan completed. Extracted {len(results)} skills."],
            "extracted_skills": results
        }
        
    result = agent.extract_skill(state)
    return {
        "messages": [f"Skill Extractor: Đã trích xuất kỹ năng mới: {result.get('skill_id', 'N/A')}" if result["status"] == "success" else "Skill Extractor: Không tìm thấy mẫu kiến thức mới."],
        "extracted_skill": result
    }

