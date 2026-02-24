import json
import datetime
from core.state import AgentState
from core.utils.llm_manager import LLMManager
from skills.google_calendar.calendar_client import CalendarClient

class ExecutiveOpsAgent:
    def __init__(self):
        self.llm = LLMManager()
        try:
            self.calendar = CalendarClient()
        except Exception as e:
            print(f"ExecutiveOpsAgent: Failed to initialize CalendarClient: {e}")
            self.calendar = None

    def process_request(self, user_input: str) -> str:
        """
        Parses the user's input and executes the appropriate calendar action.
        """
        if not self.calendar:
            return "I cannot access your calendar right now. Please check if 'credentials.json' is present and you have authenticated by running 'skills/google_calendar/authenticate.py'."

        # 1. Determine Intent & Extract Parameters
        # Use local timezone to be explicit
        now = datetime.datetime.now().astimezone().isoformat()
        prompt = f"""
        You are an Executive Operations Agent managing a Google Calendar.
        Current Time: {now}
        
        User Request: "{user_input}"
        
        Analyze the request and extract the necessary information to perform one of the following actions:
        - LIST_EVENTS: List upcoming events (e.g., asking for today's schedule, "lịch sinh hoạt hôm nay", "có lịch gì không").
        - CREATE_EVENT: Schedule a new event.
        - UPDATE_EVENT: Update an existing event.
        - DELETE_EVENT: Delete an event.
        - UNACTIONABLE: If the request is not related to the calendar.

        Return a JSON object with the following schema:
        {{
            "action": "LIST_EVENTS" | "CREATE_EVENT" | "UPDATE_EVENT" | "DELETE_EVENT" | "UNACTIONABLE",
            "parameters": {{
                "summary": "Event title (for CREATE)",
                "start_time": "ISO 8601 start time (for CREATE)",
                "end_time": "ISO 8601 end time (for CREATE)",
                "description": "Event description (optional)",
                "time_min": "ISO 8601 time to start listing from (for LIST, default to current time)",
                "max_results": 5
            }}
        }}
        
        CRITICAL: 
        1. Always map general schedule questions like "lịch hôm nay", "lịch sinh hoạt", "today's plan" to LIST_EVENTS.
        2. Output ONLY the raw JSON object. Do not wrap it in markdown blocks.
        """
        
        response = self.llm.query(prompt, complexity="L2") # Use Flash for speed
        
        try:
            # Clean up response if it contains markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            data = json.loads(response)
            action = data.get("action")
            params = data.get("parameters", {})
            
            # Helper to ensure RFC3339 (adding timezone if missing)
            def normalize_ts(ts):
                if not ts: return ts
                if 'T' in ts and not ('+' in ts or '-' in ts[len(ts)-6:] or ts.endswith('Z')):
                    return ts + "+07:00" # Default to user's local TZ
                return ts

            if action == "LIST_EVENTS":
                events = self.calendar.list_events(
                    max_results=params.get("max_results", 5),
                    time_min=normalize_ts(params.get("time_min")) or now
                )
                if not events:
                    return "Bạn không có lịch trình nào sắp tới trên Calendar."
                
                result = "📅 **Lịch trình sắp tới của bạn:**\n"
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    # Format time if it's datetime
                    if 'T' in start:
                        start_fmt = start[11:16]
                    else:
                        start_fmt = "Cả ngày"
                    result += f"- {start_fmt}: {event['summary']}\n"
                return result

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
            
            elif action == "UNACTIONABLE":
                return "Yêu cầu này không liên quan đến thao tác trên Calendar."
            else:
                print(f"[ExecutiveOps] Unhandled action '{action}' from response: {response}")
                return "I'm not sure how to help with that calendar request."

        except json.JSONDecodeError:
            print(f"[ExecutiveOps] JSON Decode Error on response: {response}")
            return f"Lỗi phân tích yêu cầu từ AI (JSON)."
        except Exception as e:
            return f"An error occurred: {e}"

def executive_ops_node(state: AgentState):
    """
    Node for the Executive Ops Agent.
    """
    agent = ExecutiveOpsAgent()
    user_input = state["messages"][-1]
    
    response = agent.process_request(user_input)
    
    return {"messages": [f"Executive Ops: {response}"]}
