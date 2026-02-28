import json
import datetime
import os
from core.state import AgentState
from core.utils.llm_manager import LLMManager
from skills.google_calendar.calendar_client import CalendarClient
from core.services.scheduler_state import scheduler_state

class ExecutiveOpsAgent:
    def __init__(self):
        self.llm = LLMManager()
        try:
            self.calendar = CalendarClient()
        except Exception as e:
            print(f"ExecutiveOpsAgent: Failed to initialize CalendarClient: {e}")
            self.calendar = None

    def _list_events_response(self, max_results: int = 10) -> str:
        """Reports exclusively the confirmed daily schedule (Lịch Chuẩn)."""
        try:
            now_dt = datetime.datetime.now()
            
            # Fetch Confirmed Schedule (Lịch Chuẩn)
            confirmed_items = scheduler_state.load_schedule()
            # Filter for today's items (simple date check)
            today_str = now_dt.strftime("%Y-%m-%d")
            standard_plan = [item for item in confirmed_items if item.get("start_time", "").startswith(today_str)]
            
            if not standard_plan:
                return "Bạn không có lịch trình chuẩn nào được chốt cho hôm nay."
            
            result = "⭐ **LỊCH CHUẨN (Đã xác nhận):**\n"
            # Sort by time
            standard_plan.sort(key=lambda x: x.get("start_time", ""))
            for item in standard_plan:
                time_str = item["start_time"][11:16] if "T" in item["start_time"] else "N/A"
                status = "✅" if item.get("is_confirmed") else "⏳"
                result += f"- {time_str}: {item['summary']} {status}\n"
            
            return result.strip()
        except Exception as e:
            print(f"[ExecutiveOps] Schedule Report Error: {e}")
            return f"Lỗi khi truy xuất lịch trình: {e}"

    def _work_report_response(self) -> str:
        """Generates a comprehensive work report combining schedule, tasks, and night jobs."""
        try:
            from core.utils.task_manager import task_manager
            from core.services.night_shift import night_shift
            
            now_dt = datetime.datetime.now()
            today_str = now_dt.strftime("%Y-%m-%d")
            user_id = os.getenv("TELEGRAM_USER_ID", "default_user")
            
            report = f"📊 **BÁO CÁO CÔNG VIỆC TỔNG HỢP ({today_str})**\n\n"
            
            # 1. Tasks Status
            pending_tasks = task_manager.get_pending_tasks(user_id)
            completed_today = task_manager.get_completed_tasks_today(user_id)
            
            report += "📝 **TRẠNG THÁI TASKS:**\n"
            if pending_tasks:
                report += f"- Đang chờ: {len(pending_tasks)}\n"
                for t in pending_tasks[:5]: # Show top 5
                    report += f"  • {t['desc']}\n"
                if len(pending_tasks) > 5:
                    report += f"  ... và {len(pending_tasks)-5} task khác.\n"
            else:
                report += "- Không có task nào đang chờ.\n"
                
            if completed_today:
                report += f"- Đã xong hôm nay: {len(completed_today)}\n"
            report += "\n"
            
            # 2. Night Shift Status
            pending_jobs = night_shift.get_pending_jobs()
            report += "🌙 **NIGHT SHIFT (QUOTA Tối ưu):**\n"
            if pending_jobs:
                report += f"- Công việc đang chờ: {len(pending_jobs)}\n"
            else:
                report += "- Hàng chờ đêm trống.\n"
            report += "\n"
            
            # 3. Schedule Summary
            schedule = self._list_events_response()
            report += schedule
            
            return report.strip()
        except Exception as e:
            print(f"[ExecutiveOps] Work Report Error: {e}")
            return f"Lỗi khi tổng hợp báo cáo công việc: {e}"

    def _is_schedule_query(self, text: str) -> bool:
        """Deterministic keyword check for strictly calendar/schedule queries."""
        lower = text.lower()
        # Strictly schedule keywords. Excluding "báo cáo" or "tổng hợp" as they need comprehensive report.
        schedule_keywords = [
            "lịch", "sinh hoạt", "hôm nay", "ngày mai", "tuần này",
            "schedule", "calendar", "upcoming", "event", "sự kiện",
            "có gì", "kế hoạch", "agenda", "plan today", "what's on"
        ]
        # If it contains "báo cáo", "tổng hợp", or "report", it's NOT a simple schedule query
        if any(kw in lower for kw in ["báo cáo", "tổng hợp", "report", "tình hình"]):
            return False
            
        return any(kw in lower for kw in schedule_keywords)

    def _get_prompt(self):
        if not hasattr(self, "_cached_prompt") or self._cached_prompt is None:
            root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../.."))
            prompt_path = os.path.join(root_dir, "prompts", "executive_ops.md")
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self._cached_prompt = f.read()
            else:
                self._cached_prompt = "You are an Executive Operations Agent."
        return self._cached_prompt

    def process_request(self, user_input: str) -> str:
        """
        Parses the user's input and executes the appropriate calendar action.
        Uses a DETERMINISTIC fast-path for schedule queries to avoid LLM misclassification.
        """
        if not self.calendar:
            return "I cannot access your calendar right now. Please check if 'credentials.json' is present and you have authenticated by running 'skills/google_calendar/authenticate.py'."

        print(f"[ExecutiveOps] Processing: '{user_input[:80]}'")

        # =============================================
        # FAST PATH: Deterministic keyword matching
        # Bypasses LLM entirely for schedule queries
        # =============================================
        if self._is_schedule_query(user_input):
            print(f"[ExecutiveOps] FAST PATH -> LIST_EVENTS (keyword match)")
            return self._list_events_response()

        # =============================================
        # SLOW PATH: LLM-based intent for complex ops
        # (create, update, delete events)
        # =============================================
        now = datetime.datetime.now().astimezone().isoformat()
        prompt_template = self._get_prompt()
        prompt = prompt_template.format(now=now, user_input=user_input)
        
        response = self.llm.query(prompt, complexity="L2")
        
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            data = json.loads(response)
            action = data.get("action")
            params = data.get("parameters", {})
            
            def normalize_ts(ts):
                if not ts: return ts
                if 'T' in ts and not ('+' in ts or '-' in ts[len(ts)-6:] or ts.endswith('Z')):
                    return ts + "+07:00"
                return ts

            if action == "LIST_EVENTS":
                return self._list_events_response()
            
            elif action == "WORK_REPORT":
                return self._work_report_response()

            elif action == "CREATE_EVENT":
                summary = params.get("summary")
                start_time = params.get("start_time")
                end_time = params.get("end_time")
                description = params.get("description")
                
                if not summary or not start_time or not end_time:
                    return "Tôi cần tên sự kiện, thời gian bắt đầu và kết thúc để tạo lịch."
                
                event = self.calendar.create_event(
                    summary, 
                    normalize_ts(start_time), 
                    normalize_ts(end_time), 
                    description
                )
                return f"✅ Đã tạo lịch: {event.get('htmlLink')}"
            
            elif action == "UPDATE_EVENT":
                return "Chức năng cập nhật lịch hiện chưa hoàn thiện. Vui lòng thao tác thủ công."
            
            elif action == "DELETE_EVENT":
                return "Chức năng xóa lịch hiện chưa hoàn thiện. Vui lòng thao tác thủ công."
            
            else:
                # Fallback: if LLM returns anything unexpected, just list events
                print(f"[ExecutiveOps] Unknown action '{action}', falling back to LIST_EVENTS")
                return self._list_events_response()

        except json.JSONDecodeError:
            print(f"[ExecutiveOps] JSON Decode Error: {response[:100]}")
            # Fallback: list events instead of showing error
            return self._list_events_response()
        except Exception as e:
            return f"An error occurred: {e}"

def executive_ops_node(state: AgentState):
    """
    Node for the Executive Ops Agent.
    """
    agent = ExecutiveOpsAgent()
    
    # Extract the last actual user message, ignoring system routing messages
    messages = state.get("messages", [])
    user_input = ""
    for msg in reversed(messages):
        if msg and isinstance(msg, str) and not msg.startswith("System"):
            user_input = msg
            break
            
    if not user_input and len(messages) > 0:
        user_input = messages[-1]

    response = agent.process_request(user_input)
    
    return {"messages": [f"Executive Ops: {response}"]}
