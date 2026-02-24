import json
import datetime
from typing import TypedDict, List, Dict, Any, Annotated
import operator

from langgraph.graph import StateGraph, END
from core.state import AgentState, merge_dicts
from core.utils.llm_manager import LLMManager
from skills.google_calendar.calendar_client import CalendarClient

class SchedulerState(AgentState):
    """Extends AgentState with specific fields for scheduling."""
    optimized_schedule: Optional[List[Dict[str, Any]]]
    conflicts: Optional[List[Dict[str, Any]]]
    roadmap_context: Optional[str]

class SchedulerAgent:
    def __init__(self):
        self.llm = LLMManager()
        try:
            self.calendar = CalendarClient()
        except Exception:
            self.calendar = None

    def _fetch_context(self, state: SchedulerState) -> Dict[str, Any]:
        """Node: Gathers calendar events and roadmap goals."""
        now = datetime.datetime.now().astimezone()
        time_min = now.isoformat()
        
        events = []
        if self.calendar:
            events = self.calendar.list_events(max_results=20, time_min=time_min)
        
        # In a real scenario, we'd read task.md and roadmap.md here
        # For now, we assume they are passed in or we use a placeholder
        roadmap = "Mục tiêu: Trở thành AI Navigator. Ưu tiên: Học máy, Đạo đức AI, Dự án mom-game."
        
        return {
            "messages": ["Hệ thống: Đã thu thập dữ liệu lịch trình và lộ trình phát triển."],
            "long_term_memory": events,
            "roadmap_context": roadmap
        }

    def _optimize_logic(self, state: SchedulerState) -> Dict[str, Any]:
        """Node: Uses LLM to optimize the schedule based on bio-data."""
        events = state.get("long_term_memory", [])
        roadmap = state.get("roadmap_context", "")
        readiness = state.get("readiness_score", 100)
        
        # Chronotype detection (simplified for now: assume morning hunter)
        # In a real scenario, this would be derived from Oura "Body Clock"
        chronotype = "Morning Hunter (Peak: 8 AM - 12 PM)" 
        
        prompt = f"""
        Bạn là chuyên gia tối ưu hóa lịch trình dựa trên thần kinh học (Bio-Adaptive Scheduler).
        
        DỮ LIỆU SINH HỌC:
        - Readiness Score: {readiness}/100
        - Chronotype: {chronotype}
        
        LỊCH TRÌNH HIỆN TẠI:
        {json.dumps(events, indent=2)}
        
        MỤC TIÊU DÀI HẠN: {roadmap}
        
        NHIỆM VỤ:
        1. Nếu Readiness < 70: Ưu tiên dời các task khó (Deep Work) sang ngày khác hoặc buổi chiều, chèn 20p NSDR vào lúc 2 PM.
        2. Nếu Readiness > 85: Đẩy các task quan trọng nhất của Lộ trình vào khung giờ vàng ({chronotype}).
        3. Đảm bảo có ít nhất 90 phút Deep Work không bị gián đoạn.
        4. Gợi ý bài tập (Boxing vs Recovery) dựa trên điểm sẵn sàng.
        
        Trả về kết quả dưới dạng JSON (recommendations).
        """
        
        response = self.llm.query(prompt, complexity="L3")
        # Parsing logic would go here
        
        return {
            "messages": [f"Scheduler AI: Đã hoàn thành phân tích tối ưu hóa.\n{response}"],
            "is_valid": True
        }

    def get_graph(self):
        workflow = StateGraph(SchedulerState)
        
        workflow.add_node("fetch_context", self._fetch_context)
        workflow.add_node("optimize", self._optimize_logic)
        
        workflow.set_entry_point("fetch_context")
        workflow.add_edge("fetch_context", "optimize")
        workflow.add_edge("optimize", END)
        
        return workflow.compile()

def scheduler_node(state: AgentState):
    """Entry point for the supervisor to call the scheduler agent."""
    agent = SchedulerAgent()
    graph = agent.get_graph()
    
    # Initialize SchedulerState from AgentState
    initial_state = state.copy()
    initial_state["optimized_schedule"] = None
    initial_state["conflicts"] = None
    initial_state["roadmap_context"] = None
    
    final_state = graph.invoke(initial_state)
    return final_state
