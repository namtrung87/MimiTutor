import json
import os
from datetime import datetime
from core.agents.universal_agent import UniversalAgent
from core.state import AgentState
from skills.commute_planner.commute_calculator import CommutePlanner
from core.utils.search_service import SearchService

class CommuteLogicAgent(UniversalAgent):
    def __init__(self):
        super().__init__()
        self.prompt_map["commute"] = "commute_meta_alchemist"
        self.commute_data_path = os.path.join(os.path.dirname(__file__), "../../commute_state.json")
        self._load_state()
        self.planner = CommutePlanner()
        self.search_service = SearchService()

    def _load_state(self):
        if os.path.exists(self.commute_data_path):
            with open(self.commute_data_path, "r", encoding="utf-8") as f:
                self.state_data = json.load(f)
        else:
            self.state_data = {
                "active_mode": "idle",
                "total_insights": 0,
                "game_rewards_pending": 0,
                "recovery_points": 0,
                "last_sync": datetime.now().isoformat()
            }

    def _save_state(self):
        self.state_data["last_sync"] = datetime.now().isoformat()
        with open(self.commute_data_path, "w", encoding="utf-8") as f:
            json.dump(self.state_data, f, indent=2, ensure_ascii=False)

    async def process_request(self, state: AgentState) -> dict:
        user_input = state["messages"][-1]
        
        # Travel Planning Logic Bridge
        if any(word in user_input.lower() for word in ["di chuyển", "phương án", "đi đâu"]):
            # Simple extraction for now
            origin = self.state_data.get("locations", {}).get("home", "Hà Nội")
            dest = user_input.replace("di chuyển", "").replace("phương án", "").replace("đến", "").strip()
            target_time = "08:00" # Default
            
            # Fetch real-time context via Firecrawl Search
            search_query = f"xe bus từ {origin} đến {dest} lộ trình chi tiết"
            live_context = self.search_service.search(search_query)
            
            # Call the planner with search grounding enabled
            plan = await self.planner.get_travel_plan(origin, dest, target_time, live_context=live_context)
            
            if "options" in plan:
                res_msg = f"📍 **Phương án di chuyển dự thảo từ {plan.get('origin')} đến {plan.get('destination')}:**\n\n"
                for opt in plan["options"]:
                    rec = " ⭐" if opt.get("is_recommended") else ""
                    res_msg += f"🔹 **{opt['mode']}**{rec}:\n   - Lộ trình: {opt['route_desc']}\n   - Thời gian: {opt['estimated_duration_min']}p | Chi phí: {opt['estimated_cost_vnd']:,}đ\n   - Xuất phát: {opt['departure_time']}\n\n"
                res_msg += f"💡 *Câu hỏi:* Lộ trình trên chỉ là dự thảo. Anh có muốn chốt chính xác đi tuyến xe bus nào, số mấy để em lưu lời nhắc chính xác cho sáng mai không?"
                return {"messages": [res_msg]}
            else:
                return {"messages": ["Lỗi: Không thể lập kế hoạch di chuyển lúc này."]}

        # Manual Route Confirmation/Override
        if any(word in user_input.lower() for word in ["chốt đi", "ngày mai đi", "tuyến số", "đi xe"]):
            # Extract the specific route info using LLM for precision
            prompt = f"Trích xuất lộ trình di chuyển mà người dùng muốn chốt: '{user_input}'. Trả về JSON: {{'route': '...', 'departure_time': '...' or null}}. Dùng Tiếng Việt."
            res = self.llm.query(prompt, complexity="L1")
            try:
                import re
                json_match = re.search(r'{{(.*?)}}', res.replace('\n', ''), re.DOTALL)
                if json_match:
                    override_data = json.loads(f"{{{json_match.group(1)}}}")
                    self.state_data["confirmed_commute"] = {
                        "date": datetime.now().strftime("%Y-%m-%d"), # Assuming for tomorrow or next day
                        "route_desc": override_data.get("route", user_input),
                        "departure_time": override_data.get("departure_time")
                    }
                    self._save_state()
                    return {"messages": [f"✅ **Đã chốt!** Em đã lưu lộ trình: *{override_data.get('route', user_input)}*. Em sẽ nhắc anh chính xác nội dung này vào sáng mai."]}
            except Exception as e:
                print(f"  [CommuteAgent] JSON extraction error: {e}")
            
            # Fallback if JSON extraction fails
            self.state_data["confirmed_commute"] = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "route_desc": user_input
            }
            self._save_state()
            return {"messages": ["✅ Ghi nhận! Em đã lưu lộ trình này để nhắc anh vào sáng mai."]}

        # Phase 3: Voice-to-Insight (Commute Mode 2.0)
        if "VOICE_TRANSCRIBED:" in user_input:
            raw_transcript = user_input.split("VOICE_TRANSCRIBED:")[1].strip()
            print(f"  [CommuteAgent] Refining noisy transcript: {raw_transcript[:50]}...")
            
            prompt = f"""
            You are the Commute Alchemist. 
            The following text is a transcript from a voice note recorded in a noisy shuttle bus.
            Refine the text, remove noise, and extract 'Mindset Changers' or 'Actionable Insights'.
            
            TRANSCRIPT:
            {raw_transcript}
            
            Format as a clear, bulleted list of 1-3 insights.
            """
            refined = self.llm.query(prompt, complexity="L2")
            self.state_data["total_insights"] += 1
            self._save_state()
            return {"messages": [f"🚌 [Commute Mode] Insight đã được tinh lọc:\n{refined}"]}

        if "ADD_INSIGHT" in user_input:
            self.state_data["total_insights"] += 1
            self._save_state()
            state["messages"].append(f"System: Insight recorded. Total: {self.state_data['total_insights']}")
            return {"messages": state["messages"]}

        # Default to LLM processing for complex commute strategy questions
        return super().process_request(state)

async def commute_agent_node(state: AgentState):
    agent = CommuteLogicAgent()
    return await agent.process_request(state)
