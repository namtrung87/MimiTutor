import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from core.utils.llm_manager import LLMManager
from core.utils.task_manager import task_manager
from core.services.night_shift import night_shift

def morning_readiness_handler(payload: Dict[str, Any]):
    """
    Synthesizes data from tasks.db and wellness sources into a Morning Briefing.
    Payload: {'user_id': 'default_user'}
    """
    llm = LLMManager()
    user_id = payload.get('user_id', 'default_user')
    
    # 1. Get Completed Tasks from Yesterday
    yesterday = datetime.now() - timedelta(days=0) # Run at night, so "today" is what we just finished
    date_str = yesterday.strftime('%Y-%m-%d')
    
    completed = task_manager.get_completed_tasks_today(user_id)
    pending = task_manager.get_pending_tasks(user_id)
    
    # 2. Get Readiness (if available)
    readiness_data = "N/A"
    try:
        from skills.wellness.oura_client import OuraClient
        oura = OuraClient()
        readiness_data = oura.get_readiness_score()
    except Exception:
        pass
        
    # 3. Fetch Next Day Schedule (simplified)
    # In reality, would read daily_schedule.json
    
    prompt = f"""
    Bạn là Chief of Staff. Hãy chuẩn bị một "Morning Readiness Report" cho ngày mai.
    
    DỮ LIỆU HÔM NAY ({date_str}):
    - Hoàn thành: {json.dumps(completed, ensure_ascii=False)}
    - Còn tồn đọng: {json.dumps(pending, ensure_ascii=False)}
    - Chỉ số Readiness dự kiến: {readiness_data}
    
    MISSION:
    1. Tóm tắt ngắn gọn thành tựu hôm nay.
    2. Chỉ ra 3 ưu tiên lớn nhất cho sáng mai để đảm bảo tối ưu hóa năng lượng (Deep Work).
    3. Đưa ra 1 lời khuyên Stoic hoặc High-Performance để bắt đầu ngày mới.
    
    Định dạng: Markdown chuyên nghiệp, sử dụng Emoji.
    """
    
    report = llm.query(prompt, complexity="L3", domain="cos")
    
    # Save to inbox
    output_dir = os.path.join("inbox", "night_shift_results")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Morning_Readiness_{datetime.now().strftime('%Y-%m-%d')}.md"
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# 🌅 Morning Readiness Briefing\n\n{report}")
        
    return {"status": "success", "file": file_path, "preview": report[:200]}

# Register the new handler
night_shift.register_handler("morning_readiness", morning_readiness_handler)
