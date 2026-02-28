import sqlite3
import json
import asyncio
import time
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from core.utils.llm_manager import LLMManager, UsageStats
from core.utils.feature_flags import feature_flags
from core.utils.bot_logger import get_logger
from core.utils.db_utils import AsyncSQLite

logger = get_logger("night_shift")

class NightShift:
    """
    Manages background jobs that run during off-hours to utilize AI quota.
    Jobs are persisted in a SQLite database.
    Configuration is loaded from data/night_shift_config.json.
    """
    CONFIG_PATH = "data/night_shift_config.json"
    
    def __init__(self, db_path="night_shift.db"):
        self.db_path = db_path
        self.db = AsyncSQLite(db_path)
        self._init_db()
        self.handlers = {}
        self.llm = LLMManager()
        self.shift_active = False # Tracks if we are currently inside the work window
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.CONFIG_PATH):
                with open(self.CONFIG_PATH, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading night shift config: {e}")
        return {"enabled": False, "jobs": {}}

    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS night_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    handler_type TEXT NOT NULL,
                    payload TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 1,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            conn.commit()
            
    def is_quota_exhausted(self) -> bool:
        """Checks if all primary LLM keys are currently exhausted."""
        try:
            # Look for GeminiProviders in LLMManager
            for provider in self.llm.providers:
                if hasattr(provider, 'key_manager'):
                    if provider.key_manager.get_key() is None:
                        return True
            return False
        except Exception:
            return False

    def register_handler(self, handler_type: str, func: Callable[[Dict[str, Any]], Any]):
        """Registers a function to handle a specific type of job."""
        self.handlers[handler_type] = func

    async def add_job(self, name: str, handler_type: str, payload: Dict[str, Any], priority: int = 1) -> int:
        """Adds a new job to the queue."""
        if not self.config.get("enabled", False):
            logger.warning(f"Night Shift is GLOBALLY DISABLED in config. Job '{name}' not added.")
            return -1
        query = '''
            INSERT INTO night_jobs (name, handler_type, payload, status, priority)
            VALUES (?, ?, ?, 'pending', ?)
        '''
        params = (name, handler_type, json.dumps(payload), priority)
        return await self.db.execute(query, params)

    async def get_pending_jobs(self) -> List[Dict[str, Any]]:
        query = '''
            SELECT * FROM night_jobs 
            WHERE status = 'pending' 
            ORDER BY priority DESC, created_at ASC
        '''
        return await self.db.fetch_all(query)

    async def get_completed_jobs_since(self, hours: int = 12) -> List[Dict[str, Any]]:
        """Retrieves jobs completed within the last X hours."""
        query = '''
            SELECT * FROM night_jobs 
            WHERE status = 'completed' 
            AND completed_at >= datetime('now', '-' || ? || ' hours')
            ORDER BY completed_at DESC
        '''
        return await self.db.fetch_all(query, (hours,))

    async def execute_job(self, job: Dict[str, Any]):
        if not self.config.get("enabled", False):
            print(f"  [NightShift] 🛑 Night Shift is GLOBALLY DISABLED. Skipping execution of job #{job['id']}.")
            return
            
        handler_type = job['handler_type']
        job_config = self.config.get("jobs", {}).get(handler_type, {})
        
        if not job_config.get("enabled", True):
            print(f"  [NightShift] 🛑 Job type '{handler_type}' is disabled. Skipping job #{job['id']}.")
            return

        todays_cost = UsageStats.get_todays_cost()
        max_cost = self.config.get("max_total_cost_vnd", 10000)
        
        if todays_cost > max_cost:
            print(f"  [NightShift] 🚩 Budget limit exceeded ({todays_cost:.1f} VND). Skipping job #{job['id']}.")
            return

        if not feature_flags.is_enabled("night_shift"):
            print(f"  [NightShift] 🛑 Night Shift is disabled via feature flags. Skipping job #{job['id']}.")
            return

        job_id = job['id']
        payload = json.loads(job['payload'])
        
        print(f"  [NightShift] Starting job #{job_id}: {job['name']} ({handler_type})")
        
        await self.db.execute("UPDATE night_jobs SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))

        try:
            handler = self.handlers.get(handler_type)
            if not handler:
                raise ValueError(f"No handler registered for type: {handler_type}")
            
            # Execute handler in a separate thread to avoid blocking the event loop
            result = await asyncio.to_thread(handler, payload)
            
            await self.db.execute('''
                UPDATE night_jobs 
                SET status = 'completed', result = ?, completed_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (json.dumps(result), job_id))
            print(f"  [NightShift] Job #{job_id} completed successfully.")
            
        except Exception as e:
            error_msg = str(e)
            print(f"  [NightShift] Job #{job_id} failed: {error_msg}")
            await self.db.execute('''
                UPDATE night_jobs 
                SET status = 'failed', error = ?, completed_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (error_msg, job_id))
            pass

    async def send_shift_summary(self):
        """Sends a summary of all jobs executed during the just-ended shift via Telegram."""
        from core.services.telegram_service import telegram_service

        query = '''
            SELECT name, status, handler_type, error 
            FROM night_jobs 
            WHERE completed_at >= datetime('now', '-12 hours')
            OR (status = 'failed' AND completed_at >= datetime('now', '-12 hours'))
            ORDER BY completed_at ASC
        '''
        jobs = await self.db.fetch_all(query)

        if not jobs:
            print("  [NightShift] No jobs to summarize for this shift.")
            return

        success_count = sum(1 for j in jobs if j['status'] == 'completed')
        failed_count = sum(1 for j in jobs if j['status'] == 'failed')

        msg = f"🌙 *Night Shift Summary Report*\n\n"
        msg += f"✅ Completed: {success_count}\n"
        msg += f"❌ Failed: {failed_count}\n\n"
        
        if jobs:
            msg += "*Job Details:*\n"
            for j in jobs:
                icon = "✅" if j['status'] == 'completed' else "❌"
                msg += f"{icon} {j['name']} ({j['handler_type']})\n"
                if j['error']:
                    msg += f"   └ Error: {str(j['error'])[:100]}...\n"

        try:
            success = await telegram_service.send_message(msg, parse_mode="Markdown")
            if success:
                logger.info(f"Final shift report sent via Telegram.")
            else:
                logger.warning(f"Failed to send final report.")
        except Exception as e:
            logger.error(f"Error sending final report: {e}")

    async def run_worker(self, force=False, window_start="21:30", window_end="07:30"):
        """
        Runs the worker loop.
        force: If True, ignores the time window.
        window_start/end: "HH:MM" format.
        """
        logger.info(f"NightShift Worker started (Force={force}, Window={window_start}-{window_end})")
        
        def to_min(s: Any):
            if isinstance(s, int):
                return s * 60
            s_str = str(s)
            if ":" not in s: return 0
            h, m = map(int, s.split(":"))
            return h * 60 + m

        w_start = to_min(window_start)
        w_end = to_min(window_end)
        
        while True:
            enabled = self.config.get("enabled", False)
            if not enabled:
                logger.info(f"Night Shift is GLOBALLY DISABLED. Worker entering dormant mode (sleeping)...")
                while not self.config.get("enabled", False):
                    # Re-load config to check if it's been enabled
                    self.config = self._load_config()
                    if self.config.get("enabled", False):
                        break
                    await asyncio.sleep(3600) # Sleep for an hour and check again
                logger.info(f"Night Shift has been RE-ENABLED. Resuming worker.")
                
            now = datetime.now()
            now_min = now.hour * 60 + now.minute
            
            if not feature_flags.is_enabled("night_shift"):
                if self.shift_active:
                    logger.info("Night Shift disabled via feature flags. Sending report.")
                    await self.send_shift_summary()
                    self.shift_active = False
                await asyncio.sleep(600)
                continue

            is_in_window = False
            
            if w_start > w_end: # Overnight window (e.g., 21:30 to 07:30)
                if now_min >= w_start or now_min < w_end:
                    is_in_window = True
            else: # Daytime window
                if w_start <= now_min < w_end:
                    is_in_window = True
                    
            if force or is_in_window:
                if not self.shift_active:
                    logger.info(f"Entering Work Window ({now.hour:02d}:{now.minute:02d})")
                    self.shift_active = True

                # Quota Protection for "Shift 2" (02:30 - 07:30)
                # Shift 2 is defined as after 2:30 AM in an overnight window
                is_shift_2 = False
                if w_start > w_end: # It is an overnight shift
                    if 2*60+30 <= now_min < w_end:
                        is_shift_2 = True
                
                if is_shift_2 and self.is_quota_exhausted():
                    logger.warning(f"QUOTA EXHAUSTED in Shift 2 ({now.hour:02d}:{now.minute:02d}).")
                    logger.info(f"Auto-shutting down Windows as requested.")
                    import subprocess
                    # Thực thi lệnh tắt máy thật của Windows sau 60 giây, ẩn cửa sổ terminal
                    subprocess.run(["shutdown", "/s", "/t", "60"], creationflags=0x08000000)
                    sys.exit(0)

                jobs = await self.get_pending_jobs()
                if jobs:
                    logger.info(f"Found {len(jobs)} pending jobs.")
                    for job in jobs:
                        await self.execute_job(job)
                        # Avoid rate limits
                        await asyncio.sleep(10)
                else:
                    logger.info(f"No pending jobs. Sleeping...")
                    await asyncio.sleep(60)
            else:
                # Outside window
                if self.shift_active:
                    logger.info(f"Exiting Work Window ({now.hour:02d}:{now.minute:02d}). Sending report.")
                    self.shift_active = False
                    await self.send_shift_summary()

                logger.info(f"Outside window ({now.hour:02d}:{now.minute:02d}). Sleeping...")
                await asyncio.sleep(300) # Check every 5 mins

# Default instance
night_shift = NightShift()

# ==========================================
# --- Built-in Handlers ---
# ==========================================

# A. Gamification (Cost of Success & Chronicles of Trust)
def story_expansion_handler(payload: Dict[str, Any]):
    """
    Generates dialogue variants, random encounters, or item descriptions.
    Payload: {'game': 'Cost of Success', 'type': 'dialogue|encounter|item', 'context': '...'}
    """
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()
    
    game = payload.get('game', 'Unknown Game')
    gen_type = payload.get('type', 'dialogue')
    context = payload.get('context', '')
    count = payload.get('count', 10) # Default to generating 10 variations
    
    prompt = f"Bạn là Narrative Designer cho game '{game}'.\nDựa trên bối cảnh: {context}\n"
    if gen_type == 'dialogue':
         prompt += f"Hãy sinh ra {count} biến thể hội thoại (Dialogue Tree branches) cho NPC này. Đảm bảo có các lựa chọn Đạo đức (Moral), Thực dụng (Pragmatic), và Nổi loạn (Rebellious)."
    elif gen_type == 'encounter':
         prompt += f"Hãy sinh ra {count} tình huống ngẫu nhiên (Random Encounters) mà người chơi có thể gặp phải. Ghi rõ reward/penalty cho mỗi tình huống."
    elif gen_type == 'item':
         prompt += f"Hãy viết mô tả chi tiết (lore) cho {count} vật phẩm (items) liên quan đến bối cảnh trên, mang đậm chất dark fantasy / cyberpunk tùy bối cảnh."
    
    res = llm.query(prompt, complexity="L2", domain="creative")
    
    if not res:
        logger.error(f"Story expansion LLM response was empty.")
        return {"status": "error", "error": "LLM returned empty response"}
        
    # Save to a markdown file in the relevant game directory
    output_dir = os.path.join("inbox", "night_shift_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Safe filename (Slugify + ASCII only + Truncate)
    import re
    safe_game = re.sub(r'[^a-zA-Z0-9]', '_', game)
    filename = f"Story_Expansion_{safe_game[:30]}_{int(time.time())}.md"
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Night Shift: Story Expansion ({game} - {gen_type})\n\n{res}")
        
    return {"status": "success", "file": file_path, "preview": res[:200] + "..."}

night_shift.register_handler("story_expansion", story_expansion_handler)

def automated_playtesting_handler(payload: Dict[str, Any]):
    """
    Simulates a player playing through a story arc to find balance issues.
    Payload: {'arc_data': 'JSON string of choices', 'persona': 'Risk-taker'}
    """
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()
    
    arc = payload.get('arc_data', '')
    persona = payload.get('persona', 'Balanced')
    
    prompt = f"""Bạn là một Game Tester và người chơi với tính cách '{persona}'.
Dưới đây là cấu trúc các lựa chọn (Dialogue Tree) của một nhiệm vụ:
{arc}

Hãy mô phỏng việc bạn chơi qua nhánh này. Đưa ra các quyết định dựa theo tính cách '{persona}'.
Sau khi chơi xong, hãy đánh giá:
1. Tính logic của cốt truyện (Có sạn nào không?)
2. Cân bằng điểm số (Nếu thưởng/phạt quá nặng)
3. Cảm xúc người chơi (Có thấy thỏa mãn/ức chế không?)"""

    res = llm.query(prompt, complexity="L3", domain="creative")

    if not res:
        return {"status": "error", "error": "LLM returned empty response"}

    output_dir = os.path.join("inbox", "night_shift_results")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Playtest_{persona}_{int(time.time())}.md"
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Night Shift: Playtest Report (Persona: {persona})\n\n{res}")
        
    return {"status": "success", "file": file_path}

night_shift.register_handler("automated_playtesting", automated_playtesting_handler)


# B. Mimi HomeTutor & Scholar Agent
def deep_memory_consolidation_handler(payload: Dict[str, Any]):
    """
    Reads daily logs and extracts deep insights into the user's learning profile.
    Payload: {'user_id': '12345', 'date': 'YYYY-MM-DD'}
    """
    from core.utils.llm_manager import LLMManager
    from core.utils.memory_manager import MemoryManager
    import glob
    llm = LLMManager()
    mem = MemoryManager()
    
    date_str = payload.get('date', datetime.now().strftime('%Y-%m-%d'))
    user_id = payload.get('user_id', 'trung')
    
    # 1. Gather all logs for the day
    try:
        from core.utils.interaction_logger import logger as db_logger
        logs = db_logger.get_daily_interactions(user_id=user_id)
        transcript = "\n".join([f"[{l['timestamp']}] User: {l['user_input']}\nAI: {l['agent_output']}" for l in logs])
    except Exception as e:
        logger.error(f"Error reading DB Logs for deep memory consolidation: {e}. Report skipped.")
        return {"status": "error", "error": f"Failed to retrieve logs: {e}"}

    if not transcript or len(transcript) < 50:
        return {"status": "skipped", "reason": "Not enough interaction data"}

    # 2. Extract Insights
    prompt = f"""Dưới đây là transcript giao tiếp của Agent với Mimi (học sinh) trong ngày {date_str}:
{transcript}

Hãy đóng vai chuyên gia giáo dục và phân tích tâm lý. Thực hiện quá trình "Deep Memory Consolidation" chi tiết:
1. **Chủ đề đã vững (Mastered Topics)**: Những khái niệm nào Mimi đã hiểu và vận dụng tốt?
2. **Chủ đề chưa vững (Struggled Topics)**: Những khái niệm nào Mimi vẫn còn mơ hồ hoặc làm sai?
3. **Câu hỏi làm tốt (Good Responses)**: Những đoạn hội thoại nào Mimi thể hiện sự tư duy, đặt câu hỏi hay hoặc trả lời logic?
4. **Câu hỏi chưa tốt (Poor Responses)**: Những đoạn Mimi biểu hiện sự chán nản, trả lời qua loa hoặc hiểu lầm trầm trọng?
5. **Phong cách học & Tâm trạng (Learning Style)**: Trạng thái hiện tại của Mimi.
6. **Lời khuyên hành động (Actionable Advice)**: Cần thay đổi gì vào ngày mai?

Định dạng JSON kết quả (CHỈ trả về JSON):
{{
  "mastered_topics": [],
  "struggled_topics": [],
  "good_responses": [],
  "poor_responses": [],
  "learning_style": "",
  "actionable_advice": []
}}"""

    res = llm.query(prompt, complexity="L2", domain="reasoning")
    
    try:
        # Extract JSON (strip markdown if any)
        if "```json" in res:
            res = res.split("```json")[1].split("```")[0]
        elif "```" in res:
            res = res.split("```")[1].split("```")[0]
            
        insights = json.loads(res.strip())
        
        # 3. Save to memory_manager
        profile_update = f"[LEARNING_PROFILE] Date: {date_str}\n"
        profile_update += f"Mastered: {', '.join(insights.get('mastered_topics', []))}\n"
        profile_update += f"Struggled: {', '.join(insights.get('struggled_topics', []))}\n"
        profile_update += f"Insights: {json.dumps(insights, ensure_ascii=False)}"
        
        mem.add_memory(profile_update, user_id=user_id, metadata={"type": "learning_profile", "date": date_str})
        
        output_dir = os.path.join("inbox", "night_shift_results")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"Mimi_Consolidation_{date_str}.md"
        file_path = os.path.join(output_dir, filename)
        
        report_content = f"# Night Shift: Báo cáo học tập Mimi chi tiết ({date_str})\n\n"
        report_content += "## ✅ Chủ đề đã vững\n" + "\n".join([f"- {g}" for g in insights.get('mastered_topics', [])]) + "\n\n"
        report_content += "## ❌ Chủ đề cần cải thiện\n" + "\n".join([f"- {g}" for g in insights.get('struggled_topics', [])]) + "\n\n"
        report_content += "## 🧠 Phong cách & Tâm trạng\n" + insights.get('learning_style', 'N/A') + "\n\n"
        report_content += "## 💡 Chiến thuật sư phạm cho ngày mai\n" + "\n".join([f"- {a}" for a in insights.get('actionable_advice', [])])
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
            
        # 4. Notify via Telegram
        from core.services.telegram_service import telegram_service
        telegram_msg = f"📊 *Báo cáo học tập Mimi ({date_str})*\n\n"
        telegram_msg += f"✅ *Vững:* {', '.join(insights.get('mastered_topics', []))}\n"
        telegram_msg += f"⚠️ *Yếu:* {', '.join(insights.get('struggled_topics', []))}\n\n"
        telegram_msg += f"💡 *Lời khuyên:* {insights.get('actionable_advice', [''])[0]}"
        
        try:
            telegram_service.send_message_sync(telegram_msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send memory consolidation telegram: {e}")
        
        return {"status": "success", "file": file_path}
    except Exception as e:
         return {"status": "error", "error": str(e), "raw": res}

night_shift.register_handler("deep_memory_consolidation", deep_memory_consolidation_handler)


# C. TrendScout Agent
def deep_research_handler(payload: Dict[str, Any]):
    """
    Summarizes massive documents or transcripts.
    Payload: {'source_url_or_path': 'path/to/report.pdf', 'topic': 'Finance AI'}
    """
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()
    
    source = payload.get('source_url_or_path')
    topic = payload.get('topic', 'General Analysis')
    
    # Mocking document loading. In reality, use document_loader.py
    # If source is a URL, we'd fetch it. If a file, we read it.
    try:
        from core.document_loader import process_document
        doc_content = process_document(source)
    except Exception as e:
        doc_content = f"Could not load {source}: {e}"

    # Truncate to save some sanity if it's too big, though Gemini Pro has 2M tokens
    doc_content = doc_content[:150000] # roughly 50k tokens

    prompt = f"""Tiến hành Deep Research cho chủ đề: '{topic}'.
Tài liệu cung cấp (có thể rất dài):
{doc_content}

Nhiệm vụ:
1. Tóm tắt Executive Summary (Tổng quan).
2. Trích xuất các dữ liệu/thống kê quan trọng nhất (làm thành dạng bảng Markdown).
3. Đánh giá tính khả thi và tác động của các xu hướng này đến thị trường Việt Nam.
4. Gợi ý 3 hành động thực tiễn."""

    res = llm.query(prompt, complexity="L2", domain="research")

    if not res:
        return {"status": "error", "error": "LLM returned empty response"}

    output_dir = os.path.join("inbox", "night_shift_results")
    os.makedirs(output_dir, exist_ok=True)
    
    # Safe filename (Slugify + ASCII only + Truncate)
    import re
    safe_topic = re.sub(r'[^a-zA-Z0-9]', '_', topic)
    filename = f"DeepResearch_{safe_topic[:40]}_{int(time.time())}.md"
    file_path = os.path.join(output_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Night Shift: Deep Research - {topic}\nSource: {source}\n\n{res}")
        
    return {"status": "success", "file": file_path}

night_shift.register_handler("deep_research", deep_research_handler)


# D. Codebase & DevTools
def code_audit_and_test_handler(payload: Dict[str, Any]):
    """
    Scans a directory, reviews code, suggests refactoring, and writes unit tests.
    Payload: {'target_dir': 'core/agents'}
    """
    from core.utils.llm_manager import LLMManager
    import glob
    llm = LLMManager()
    
    target_dir = payload.get('target_dir', 'core/utils')
    
    # Read files
    files_content = ""
    for filepath in glob.glob(f"{target_dir}/**/*.py", recursive=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                files_content += f"\n\n--- FILE: {filepath} ---\n{content}\n"
        except Exception:
            pass
            
    # Prune content to save tokens
    from core.utils.llm_manager import ContextPruner
    files_content = ContextPruner.prune_text(files_content, max_tokens=15000)

    prompt = f"""Thực hiện Toàn diện Code Review & Auto-Testing cho các file Python sau:
{files_content}

Yêu cầu (sử dụng tối đa khả năng suy luận):
1. Code Review: Phân tích kiến trúc, tìm code smells, các hàm quá phức tạp.
2. Refactoring Suggestions: Cung cấp cụ thể đoạn code mới để tối ưu hóa hiệu năng hoặc đọc hiểu tốt hơn.
3. Unit Tests: Tự động viết source code cho 2-3 Unit Tests (pytest) quan trọng nhất cho logic cốt lõi. Gói code trong ```python block.
4. Documentation: Viết nháp một đoạn README/Docstring cho module này."""

    res = llm.query(prompt, complexity="L3", domain="reasoning")

    if not res:
        return {"status": "error", "error": "LLM returned empty response"}

    output_dir = os.path.join("inbox", "night_shift_results")
    os.makedirs(output_dir, exist_ok=True)
    
    dir_name = target_dir.replace('/', '_').replace('\\', '_')
    filename = f"Code_Audit_{dir_name}_{int(time.time())}.md"
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Night Shift: Code Audit ({target_dir})\n\n{res}")
        
    return {"status": "success", "file": file_path}

night_shift.register_handler("code_audit_and_test", code_audit_and_test_handler)


# ==========================================
# E. Content & Personal Branding (Growth)
# ==========================================

# E1. Auto Content Pipeline
def auto_content_pipeline_handler(payload: Dict[str, Any]):
    """
    Runs the full ContentCurator + GrowthAgent pipeline overnight.
    Reads the latest TrendScout briefing, generates posts for ALL audience
    personas × ALL platforms, and saves them for morning approval.
    Payload: {'audience_filter': None, 'platform_filter': None}
    """
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()

    audience_filter = payload.get('audience_filter')
    platform_filter = payload.get('platform_filter')

    # 1. Load resources
    personas_path = os.path.join("08_Growth_Branding", "audience_personas.json")
    prompt_path = os.path.join("prompts", "content_curator_social.md")
    briefing_dir = os.path.join("11_Personal_Learning", "summaries")

    try:
        with open(personas_path, "r", encoding="utf-8") as f:
            personas_data = json.loads(f.read())
        personas = personas_data.get("personas", {})
        platform_config = personas_data.get("platform_config", {})
    except Exception as e:
        return {"status": "error", "error": f"Failed to load personas: {e}"}

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except Exception as e:
        prompt_template = ""

    # 2. Get latest TrendScout briefing
    briefing_text = None
    try:
        import glob
        briefing_files = sorted(glob.glob(os.path.join(briefing_dir, "*.md")), reverse=True)
        if briefing_files:
            with open(briefing_files[0], "r", encoding="utf-8") as f:
                briefing_text = f.read()
    except Exception:
        pass

    if not briefing_text or len(briefing_text) < 50:
        # Fallback: generate a quick trend summary
        briefing_text = llm.query(
            "Hãy tóm tắt 5 xu hướng AI, Tài chính, và Giáo dục đáng chú ý nhất hôm nay. "
            "Viết bằng tiếng Việt, ngắn gọn, có số liệu nếu có.",
            complexity="L2", domain="research"
        )

    # 3. Generate posts for each persona × platform
    all_posts = {}
    personas_to_process = personas
    if audience_filter and audience_filter in personas:
        personas_to_process = {audience_filter: personas[audience_filter]}

    for persona_id, persona in personas_to_process.items():
        platforms = persona.get("platforms", ["facebook"])
        if platform_filter:
            platforms = [p for p in platforms if p == platform_filter]

        print(f"  [NightShift:E1] Generating for {persona['label']} → {platforms}")
        audience_posts = {}

        for platform in platforms:
            p_config = platform_config.get(platform, {})
            max_chars = p_config.get("max_chars", 2000)

            prompt = f"""Bạn là ContentCurator, chuyên gia nội dung & personal branding.
Biến insight từ báo cáo TrendScout thành bài đăng MXH có giá trị thực sự.

Báo cáo TrendScout hôm nay:
{briefing_text[:3000]}

Đối tượng: {persona.get('label', '')}
Pain points: {', '.join(persona.get('pain_points', [])[:3])}
Tone: {persona.get('tone', 'professional')}
Platform: {platform.upper()}
Max chars: {max_chars}
Hashtags gợi ý: {', '.join(persona.get('hashtags', [])[:5])}

Viết BÀI ĐĂNG (CHỈ trả về nội dung, không giải thích):"""

            try:
                post = llm.query(prompt, complexity="L2", domain="creative")
                if post:
                    audience_posts[platform] = post[:max_chars]
                    print(f"    ✅ {platform}: {len(post)} chars")
                # Rate limit protection
                time.sleep(3)
            except Exception as e:
                print(f"    ❌ {platform}: {e}")

        if audience_posts:
            all_posts[persona_id] = audience_posts

    # 4. Save results
    output_dir = os.path.join("08_Growth_Branding", "curated")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"night_curated_{timestamp}.json")

    data = {
        "id": f"night_curated_{timestamp}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "created": datetime.now().isoformat(),
        "source": "night_shift_auto_pipeline",
        "status": "pending_approval",
        "posts": all_posts,
        "stats": {
            "audiences": len(all_posts),
            "total_posts": sum(len(v) for v in all_posts.values()),
        },
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Also save a human-readable markdown summary
    md_path = os.path.join("inbox", "night_shift_results", f"Content_Pipeline_{timestamp}.md")
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Night Shift: Auto Content Pipeline ({data['date']})\n\n")
        f.write(f"**Total:** {data['stats']['total_posts']} posts for {data['stats']['audiences']} audiences\n\n")
        for aud_id, platforms in all_posts.items():
            label = personas.get(aud_id, {}).get("label", aud_id)
            f.write(f"## {label}\n\n")
            for plat, content in platforms.items():
                f.write(f"### {plat.upper()}\n\n{content}\n\n---\n\n")

    return {
        "status": "success",
        "file": filepath,
        "summary_file": md_path,
        "total_posts": data["stats"]["total_posts"],
    }

night_shift.register_handler("auto_content_pipeline", auto_content_pipeline_handler)


# E2. Weekly Content Calendar Generator
def weekly_calendar_gen_handler(payload: Dict[str, Any]):
    """
    Generates the content calendar for the upcoming week.
    Payload: {'week_offset': 1}  (1 = next week, 0 = this week)
    """
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()

    week_offset = payload.get('week_offset', 1)

    # 1. Load Content Roadmap
    roadmap_path = os.path.join("08_Growth_Branding", "Content_Roadmap.md")
    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            roadmap = f.read()
    except Exception:
        roadmap = "No roadmap found."

    # 2. Load audience personas summary
    personas_path = os.path.join("08_Growth_Branding", "audience_personas.json")
    try:
        with open(personas_path, "r", encoding="utf-8") as f:
            personas_data = json.loads(f.read())
        audiences = [p.get("label", "") for p in personas_data.get("personas", {}).values()]
    except Exception:
        audiences = ["General"]

    # 3. Get latest TrendScout briefing for context
    briefing_dir = os.path.join("11_Personal_Learning", "summaries")
    trend_context = ""
    try:
        import glob
        briefing_files = sorted(glob.glob(os.path.join(briefing_dir, "*.md")), reverse=True)
        if briefing_files:
            with open(briefing_files[0], "r", encoding="utf-8") as f:
                trend_context = f.read()[:2000]
    except Exception:
        pass

    # 4. Calculate target week
    from datetime import timedelta
    today = datetime.now()
    target_monday = today + timedelta(days=(7 * week_offset - today.weekday()))
    week_label = target_monday.strftime("%Y-W%W")

    prompt = f"""Bạn là Content Strategist cho thương hiệu cá nhân "Nguyễn Nam Trung" - FinovAItor / Gameducator.

## Content Roadmap hiện tại:
{roadmap}

## Đối tượng mục tiêu:
{', '.join(audiences)}

## Xu hướng gần đây (TrendScout):
{trend_context[:1500]}

## Nhiệm vụ:
Lên lịch nội dung chi tiết cho tuần {week_label} (từ {target_monday.strftime('%d/%m')} đến {(target_monday + timedelta(days=6)).strftime('%d/%m')}).

Cho mỗi ngày (Thứ 2 → Chủ Nhật), chỉ định:
| Ngày | Platform | Series/Pillar | Hook (Tiêu đề gợi ý) | Audience | Format |
|------|----------|---------------|----------------------|----------|--------|

Quy tắc:
- Mỗi ngày tối đa 2 bài (1 chính, 1 phụ)
- Đa dạng platform (không đăng liên tục 1 nền tảng)
- Đảm bảo cover đủ 3 pillars trong tuần
- Thứ 7 và Chủ Nhật: nội dung nhẹ nhàng (storytelling, reflection)
- Viết bằng Tiếng Việt, giữ thuật ngữ kỹ thuật tiếng Anh.
"""

    res = llm.query(prompt, complexity="L3", domain="creative")

    # Save
    output_dir = os.path.join("08_Growth_Branding")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"weekly_content_calendar_{week_label}.md"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Weekly Content Calendar: {week_label}\n")
        f.write(f"*Auto-generated by Night Shift on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(res)

    return {"status": "success", "file": file_path, "week": week_label}

night_shift.register_handler("weekly_calendar_gen", weekly_calendar_gen_handler)


# ==========================================
# F. Wellness & High Performance
# ==========================================

# F1. Nightly Wellness Digest
def wellness_digest_handler(payload: Dict[str, Any]):
    """
    Aggregates data from Oura, Wger, and Sparky to produce a weekly wellness report.
    Payload: {'period': 'weekly'}
    """
    from core.utils.llm_manager import LLMManager
    llm = LLMManager()

    period = payload.get('period', 'weekly')

    # 1. Collect data from all wellness sources
    wellness_data = {}

    # Oura (Readiness / Sleep)
    try:
        from skills.wellness.oura_client import OuraClient
        oura = OuraClient()
        wellness_data["oura_readiness"] = oura.get_readiness_score()
        print(f"  [NightShift:F1] Oura data collected.")
    except Exception as e:
        wellness_data["oura_readiness"] = f"Unavailable: {e}"

    # Wger (Workouts)
    try:
        from skills.wellness.wger_client import WgerClient
        wger = WgerClient()
        wellness_data["wger_workouts"] = wger.get_workout_plans()
        print(f"  [NightShift:F1] Wger data collected.")
    except Exception as e:
        wellness_data["wger_workouts"] = f"Unavailable: {e}"

    # Sparky (Body Metrics)
    try:
        from skills.wellness.sparky_client import SparkyClient
        sparky = SparkyClient()
        wellness_data["sparky_metrics"] = sparky.get_metrics()
        print(f"  [NightShift:F1] Sparky data collected.")
    except Exception as e:
        wellness_data["sparky_metrics"] = f"Unavailable: {e}"

    # Performance protocols
    try:
        from skills.wellness.performance_protocols import PerformanceProtocols
        protocols = PerformanceProtocols()
        wellness_data["protocols"] = {
            "morning": protocols.get_morning_checklist(),
            "recovery": protocols.get_recovery_advice("tired"),
        }
    except Exception:
        pass

    # 2. AI Analysis
    data_str = json.dumps(wellness_data, indent=2, default=str, ensure_ascii=False)

    prompt = f"""Bạn là Wellness Performance Coach (kết hợp Huberman Lab + Medicine 3.0 + Peter Attia).
Dưới đây là dữ liệu sức khỏe thu thập được ({period}):

{data_str}

Hãy phân tích và tạo báo cáo Wellness Digest:

1. **Tổng quan sức khỏe**: Readiness Score, HRV trend, Sleep Quality (nếu dữ liệu có).
2. **Phân tích tập luyện**: Volume, Intensity, so sánh với tuần trước.
3. **Body Composition**: Cân nặng, Body Fat (nếu dữ liệu có).
4. **Đánh giá Recovery**: Dựa trên dữ liệu, người dùng đang recovery tốt hay cần nghỉ ngơi.
5. **Khuyến nghị tuần tới**:
   - Zone 2 cardio: bao nhiêu phút/tuần
   - MMA/Boxing: nên tập bao nhiêu buổi
   - Strength: có cần deload không
   - Nutrition: gợi ý điều chỉnh (IF schedule, macro split)
   - Sleep: gợi ý cải thiện (nếu cần)
6. **Morning Protocol Check**: Nhắc lại Huberman Morning Routine nếu Readiness < 70%.

Viết bằng Tiếng Việt, ngắn gọn, sử dụng emoji để highlight metric."""

    res = llm.query(prompt, complexity="L3", domain="reasoning")

    # 3. Save report
    output_dir = os.path.join("inbox", "night_shift_results")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Wellness_Digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Night Shift: Wellness Digest ({period})\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write(res)
        f.write(f"\n\n---\n## Raw Data\n```json\n{data_str}\n```")

    return {"status": "success", "file": file_path}

night_shift.register_handler("wellness_digest", wellness_digest_handler)
