"""
Unified Chatbot Handler: AI-powered responses for Facebook, Zalo OA, and Telegram.

Receives messages from any platform via webhooks, generates AI responses,
and sends them back through the appropriate channel.
"""
import os
import json
import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from core.utils.llm_manager import LLMManager
from dotenv import load_dotenv

load_dotenv()


# ─── Conversation Memory (Simple In-Memory) ───────────────────────
class ConversationMemory:
    """Tracks recent conversation context per user per platform."""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._store: Dict[str, List[Dict[str, str]]] = {}
    
    def _key(self, platform: str, user_id: str) -> str:
        return f"{platform}:{user_id}"
    
    def add(self, platform: str, user_id: str, role: str, content: str):
        key = self._key(platform, user_id)
        if key not in self._store:
            self._store[key] = []
        self._store[key].append({"role": role, "content": content, "ts": datetime.datetime.now().isoformat()})
        # Trim to max history
        if len(self._store[key]) > self.max_history:
            self._store[key] = self._store[key][-self.max_history:]
    
    def get_context(self, platform: str, user_id: str) -> str:
        key = self._key(platform, user_id)
        history = self._store.get(key, [])
        if not history:
            return ""
        return "\n".join([f"[{m['role']}]: {m['content']}" for m in history[-5:]])
    
    def clear(self, platform: str, user_id: str):
        key = self._key(platform, user_id)
        self._store.pop(key, None)


# ─── Platform Response Configs ─────────────────────────────────────
PLATFORM_CONFIGS = {
    "facebook_messenger": {
        "max_response_chars": 2000,
        "tone": "thân thiện, chuyên nghiệp",
        "response_style": "Trả lời ngắn gọn, rõ ràng. Dùng emoji vừa phải.",
    },
    "zalo_oa": {
        "max_response_chars": 1500,
        "tone": "lịch sự, gần gũi",
        "response_style": "Trả lời chi tiết hơn. Gợi ý hành động cụ thể.",
    },
    "telegram": {
        "max_response_chars": 4096,
        "tone": "trực tiếp, sâu sắc",
        "response_style": "Có thể trả lời dài hơn với markdown formatting.",
    },
    "discord": {
        "max_chars": 2000,
        "tone": "vừa phải, hỗ trợ",
        "response_style": "Dùng markdown tốt, code blocks nếu cần, và emoji.",
    },
}


class ChatbotHandler:
    """
    Unified chatbot that handles messages from multiple platforms.
    
    Usage:
        handler = ChatbotHandler()
        response = handler.handle_message(
            platform="facebook_messenger",
            user_id="12345",
            user_name="Nguyen Van A",
            message="Tôi muốn tìm hiểu về khóa học AI"
        )
    """
    
    def __init__(self):
        self.llm = LLMManager(app_name="telegram_bot")
        self.memory = ConversationMemory()
        self.log_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "08_Growth_Branding" / "chat_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Load business knowledge base
        self.knowledge_base = self._load_knowledge()
    
    def _load_knowledge(self) -> str:
        """Load business context for AI responses."""
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        knowledge_parts = []
        
        # Load growth prompt as base personality
        prompt_path = base_dir / "prompts" / "growth_branding_specialist.md"
        if prompt_path.exists():
            knowledge_parts.append(prompt_path.read_text(encoding="utf-8"))
        
        # Add any FAQ or product info if available
        faq_path = base_dir / "08_Growth_Branding" / "faq.md"
        if faq_path.exists():
            knowledge_parts.append(faq_path.read_text(encoding="utf-8"))
        
        full_kb = "\n\n".join(knowledge_parts) if knowledge_parts else "Bạn là trợ lý AI thông minh, chuyên tư vấn về AI và công nghệ."
        
        # Prune to save tokens (approx 2000 chars limit)
        if len(full_kb) > 2000:
            print(f"  [Chatbot] ⚠️ Knowledge Base too large ({len(full_kb)} chars). Pruning to 2000.")
            full_kb = full_kb[:2000] + "\n... [Knowledge Pruned to save tokens]"
            
        return full_kb
    
    def handle_message(
        self,
        platform: str,
        user_id: str,
        user_name: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process an incoming message and generate an AI response.
        
        Args:
            platform: 'facebook_messenger', 'zalo_oa', or 'telegram'
            user_id: Unique user identifier on the platform
            user_name: Display name of the user
            message: The user's message text
            metadata: Optional platform-specific metadata
            
        Returns:
            AI-generated response string
        """
        print(f"  [Chatbot] 💬 [{platform}] {user_name} ({user_id}): {message[:50]}...")
        
        # Get platform config
        config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS["telegram"])
        
        # Store user message in memory
        self.memory.add(platform, user_id, "user", message)
        
        # Get conversation context
        context = self.memory.get_context(platform, user_id)
        
        # Build prompt
        prompt = f"""
{self.knowledge_base}

BẠN ĐANG TRẢ LỜI KHÁCH HÀNG TRÊN: {platform.upper()}
TÊN KHÁCH: {user_name}
TONE: {config['tone']}
STYLE: {config['response_style']}
TỐI ĐA: {config['max_response_chars']} ký tự

LỊCH SỬ HỘI THOẠI:
{context}

TIN NHẮN MỚI NHẤT CỦA KHÁCH:
{message}

QUY TẮC:
1. Trả lời bằng tiếng Việt
2. Là trợ lý chuyên nghiệp, không nói mình là AI
3. Nếu khách hỏi về giá/dịch vụ cụ thể mà bạn không biết → gợi ý liên hệ trực tiếp
4. Luôn kết thúc bằng câu hỏi mở hoặc gợi ý hành động tiếp theo
5. Nếu khách có vẻ không hài lòng → thể hiện sự đồng cảm, chuyển sang hỗ trợ manual

TRẢ LỜI (CHỈ nội dung phản hồi, không giải thích):
"""
        
        try:
            response = self.llm.query_sync(prompt, complexity="L1")
            
            if not response:
                response = "Cảm ơn bạn đã nhắn tin! Mình sẽ phản hồi ngay khi có thể. 😊"
            
            # Truncate to platform limit
            response = response[:config["max_response_chars"]]
            
        except Exception as e:
            print(f"  [Chatbot] Error generating response: {e}")
            response = "Cảm ơn bạn đã nhắn tin. Mình sẽ liên hệ lại sớm nhé! 🙏"
        
        # Store bot response in memory
        self.memory.add(platform, user_id, "bot", response)
        
        # Log conversation
        self._log_conversation(platform, user_id, user_name, message, response)
        
        print(f"  [Chatbot] ✅ Response generated ({len(response)} chars)")
        return response
    
    def _log_conversation(self, platform: str, user_id: str, user_name: str, message: str, response: str):
        """Log conversation for analytics and improvement."""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "platform": platform,
            "user_id": user_id,
            "user_name": user_name,
            "message": message,
            "response": response,
        }
        
        log_file = self.log_dir / f"chat_{datetime.datetime.now().strftime('%Y%m%d')}.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"  [Chatbot] Log error: {e}")
    
    def get_escalation_needed(self, platform: str, user_id: str) -> bool:
        """Check if conversation should be escalated to human."""
        context = self.memory.get_context(platform, user_id)
        if not context:
            return False
        
        # Simple heuristic: escalate if user mentions certain keywords
        escalation_keywords = ["không hài lòng", "complaint", "khiếu nại", "refund", "hoàn tiền", "gặp quản lý"]
        return any(kw in context.lower() for kw in escalation_keywords)


# ─── Webhook Handlers (for FastAPI/Flask integration) ──────────────

# Global instance
chatbot = ChatbotHandler()


def handle_facebook_webhook(data: Dict[str, Any]) -> Optional[str]:
    """Process incoming Facebook Messenger webhook payload."""
    try:
        entry = data.get("entry", [{}])[0]
        messaging = entry.get("messaging", [{}])[0]
        
        sender_id = messaging.get("sender", {}).get("id", "unknown")
        message_text = messaging.get("message", {}).get("text", "")
        
        if not message_text:
            return None
        
        return chatbot.handle_message(
            platform="facebook_messenger",
            user_id=sender_id,
            user_name=f"FB_{sender_id}",
            message=message_text,
            metadata=data,
        )
    except Exception as e:
        print(f"  [Chatbot] Facebook webhook error: {e}")
        return None


def handle_zalo_webhook(data: Dict[str, Any]) -> Optional[str]:
    """Process incoming Zalo OA webhook payload."""
    try:
        event_name = data.get("event_name", "")
        
        if event_name != "user_send_text":
            return None
        
        sender_id = data.get("sender", {}).get("id", "unknown")
        message_text = data.get("message", {}).get("text", "")
        
        if not message_text:
            return None
        
        return chatbot.handle_message(
            platform="zalo_oa",
            user_id=sender_id,
            user_name=f"Zalo_{sender_id}",
            message=message_text,
            metadata=data,
        )
    except Exception as e:
        print(f"  [Chatbot] Zalo webhook error: {e}")
        return None


def handle_discord_webhook(data: Dict[str, Any]) -> Optional[str]:
    """Process incoming Discord webhook/interaction payload."""
    try:
        # Simplistic Discord interaction/webhook parsing
        user_id = data.get("author", {}).get("id", "unknown")
        user_name = data.get("author", {}).get("username", "discord_user")
        message_text = data.get("content", "")
        
        if not message_text:
            return None
        
        return chatbot.handle_message(
            platform="discord",
            user_id=user_id,
            user_name=user_name,
            message=message_text,
            metadata=data,
        )
    except Exception as e:
        print(f"  [Chatbot] Discord webhook error: {e}")
        return None


# ─── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    handler = ChatbotHandler()
    
    # Simulate a conversation
    print("\n=== Test: Facebook Messenger ===")
    r1 = handler.handle_message("facebook_messenger", "user_001", "Nguyên", "Xin chào, tôi muốn tìm hiểu về khóa học AI")
    print(f"Bot: {r1}\n")
    
    r2 = handler.handle_message("facebook_messenger", "user_001", "Nguyên", "Giá khóa học bao nhiêu?")
    print(f"Bot: {r2}\n")
    
    print("=== Test: Zalo OA ===")
    r3 = handler.handle_message("zalo_oa", "zalo_001", "Trung", "Cho mình hỏi về dịch vụ tư vấn AI")
    print(f"Bot: {r3}\n")
