import os
import asyncio
from core.utils.gmail_client import GmailClient
from core.utils.llm_manager import LLMManager
from core.services.telegram_service import telegram_service

class GmailExecutiveAgent:
    """
    Agent responsible for checking unread emails, summarizing them, 
    and reporting to the user via Telegram.
    """
    def __init__(self):
        self.gmail = GmailClient()
        self.llm = LLMManager()

    async def run_daily_check(self):
        print("[*] Gmail Executive: Starting daily check...")
        
        # 1. Fetch unread messages
        messages = self.gmail.list_messages(query="is:unread", max_results=10)
        if not messages:
            print("[*] No unread messages found.")
            await telegram_service.send_message("📧 **Gmail Report**: Hộp thư của thầy không có thư mới chưa đọc. Chúc thầy một ngày làm việc hiệu quả!")
            return

        report_items = []
        for m in messages:
            details = self.gmail.get_message(m['id'])
            
            # 2. Analyze with LLM (L2 to save budget, L3 for high importance if needed)
            analysis_prompt = f"""
            Bạn là một trợ lý điều hành cấp cao. Hãy phân tích email sau:
            FROM: {details['sender'] if 'sender' in details else details.get('from')}
            SUBJECT: {details['subject']}
            BODY: {details['body'][:2000]}
            
            Nhiệm vụ:
            1. Tóm tắt nội dung chính trong 2 câu.
            2. Đánh giá độ quan trọng trên thang điểm 10 (1: Rác, 10: Khẩn cấp/Quan trọng).
            3. Đề xuất hành động (Trả lời gấp, Đọc sau, Bỏ qua).
            
            Trả về định dạng:
            **Tóm tắt**: <nội dung>
            **Độ quan trọng**: <số>/10
            **Hành động**: <đề xuất>
            """
            
            summary = self.llm.query(analysis_prompt, complexity="L2")
            
            item_text = f"📩 **{details['subject']}**\n- Người gửi: {details.get('from')}\n{summary}"
            item_text += f"\n[BUTTON:✍️ Tạo nháp trả lời:gmail_reply_{m['id']}]"
            report_items.append(item_text)

        # 3. Consolidate and send via Telegram
        final_report = "📑 **GMAIL EXECUTIVE SUMMARY**\n\n" + "\n\n---\n\n".join(report_items)
        
        # Telegram has a char limit, handle if needed
        if len(final_report) > 4000:
            parts = [final_report[i:i+4000] for i in range(0, len(final_report), 4000)]
            for p in parts:
                await telegram_service.send_message(p)
        else:
            await telegram_service.send_message(final_report)
        
        print("[*] Gmail Executive: Report sent to Telegram.")

if __name__ == "__main__":
    agent = GmailExecutiveAgent()
    asyncio.run(agent.run_daily_check())
