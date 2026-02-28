import json
import re
from typing import Dict, Any
from core.utils.llm_manager import LLMManager

class HomeworkParser:
    def __init__(self):
        self.llm = LLMManager()

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parses raw text from a teacher's message and extracts homework details.
        """
        prompt = f"""
        Bạn là trợ lý học tập cho bé Bông Bông. Nhiệm vụ của bạn là đọc tin nhắn dặn dò của giáo viên và trích xuất danh sách bài tập về nhà.
        
        NỘI DUNG TIN NHẮN:
        \"\"\"
        {text}
        \"\"\"
        
        YÊU CẦU:
        1. Liệt kê các môn học và bài tập tương ứng.
        2. Tóm tắt ngắn gọn, dễ hiểu.
        3. Xuất kết quả dưới dạng JSON với cấu trúc:
        {{
            "summary": "Tiêu đề ngắn (VD: Bài tập ngày 25/02)",
            "tasks": [
                {{"subject": "Tên môn", "description": "Nội dung bài tập"}}
            ],
            "deadline": "Hạn nộp (nếu có, không có thì để null)"
        }}

        TRẢ LỜI BẰNG JSON NGUYÊN BẢN (KHÔNG KÈM MARKDOWN):
        """
        
        try:
            response = self.llm.query(prompt, complexity="L1")
            # Basic cleanup
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {"summary": "Bài tập về nhà", "tasks": [], "deadline": None}
        except Exception as e:
            print(f"Error parsing homework: {e}")
            return {"summary": "Lỗi phân tích bài tập", "tasks": [], "deadline": None}

    def format_for_telegram(self, parsed_data: Dict[str, Any]) -> str:
        """Formats the parsed data into a beautiful Telegram message."""
        summary = parsed_data.get("summary", "Bài tập về nhà")
        tasks = parsed_data.get("tasks", [])
        
        msg = f"📚 *{summary}*\n\n"
        if not tasks:
            msg += "Không tìm thấy nội dung bài tập cụ thể."
        else:
            for t in tasks:
                msg += f"🔹 *{t['subject']}*: {t['description']}\n"
        
        deadline = parsed_data.get("deadline")
        if deadline:
            msg += f"\n⏰ *Hạn nộp:* {deadline}"
        
        return msg
