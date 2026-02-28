import os
import time
from core.utils.google_researcher import GoogleResearcher
from core.utils.gamma_client import GammaClient
from core.utils.llm_manager import LLMManager

class DriveEducatorAgent:
    """
    Agent that searches Drive for educational content and generates 
    professional presentations using the Gamma API.
    """
    def __init__(self):
        self.researcher = GoogleResearcher()
        self.gamma = GammaClient()
        self.llm = LLMManager()

    def generate_session_materials(self, topic):
        print(f"[*] Drive Educator: Researching session materials for '{topic}'...")
        
        # 1. Use researcher to gather context from Drive
        research_notes = self.researcher.research_topic_in_drive(topic)
        if "No documents found" in research_notes:
             print(f"[!] Warning: {research_notes}")
             # We can still proceed with general knowledge if the user wants,
             # but here we'll assume we need grounding.
        
        # 2. Refine research notes into a Gamma-optimized prompt
        # We want to ensure it follows PACE-X 2.0
        refinement_prompt = f"""
        Dựa trên kết quả nghiên cứu sau đây về chủ đề "{topic}":
        ---
        {research_notes}
        ---
        
        Hãy soạn thảo một bản đề cương chi tiết cho bài trình chiếu (Presentation) chuẩn khung PACE-X 2.0.
        Yêu cầu:
        1. Ngôn ngữ: Tiếng Việt chuyên nghiệp.
        2. Cấu trúc gồm: Problem, Analysis, Concept, Execution, eXperience.
        3. Nội dung phải thực tế, giàu dữ liệu và có tính ứng dụng cao.
        
        Định dạng trả về: Một đoạn văn bản dài, chi tiết để tôi đưa trực tiếp vào Gamma API.
        """
        
        gamma_input = self.llm.query(refinement_prompt, complexity="L3")
        
        # 3. Trigger Gamma Generation
        print(f"[*] Drive Educator: Sending content to Gamma API...")
        try:
            # We use the raw generate since polling isn't in core GammaClient yet
            # Let's add polling here for now or update GammaClient
            result = self.gamma.generate_presentation(gamma_input, text_mode="preserve")
            gen_id = result.get("generationId")
            
            if not gen_id:
                return None
                
            print(f"[*] Generation ID: {gen_id}. Polling...")
            for i in range(20):
                time.sleep(10)
                status_res = self.gamma.get_generation_status(gen_id)
                status = status_res.get("status")
                if status == "completed":
                    url = status_res.get("gammaUrl")
                    print(f"[SUCCESS] Materials generated: {url}")
                    return url
                elif status == "failed":
                    print("[!] Gamma Report: Generation failed.")
                    return None
            return None
        except Exception as e:
            print(f"[ERROR] Gamma integration error: {e}")
            return None

if __name__ == "__main__":
    agent = DriveEducatorAgent()
    # Test with a specific session
    topic = "Business Analysis Buổi 2: Phân tích quy trình"
    materials_url = agent.generate_session_materials(topic)
    if materials_url:
        print(f"\n✅ Link bài giảng mới của thầy: {materials_url}")
