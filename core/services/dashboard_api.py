"""
Phase 15: Dashboard Status API
Serves real-time system status for the Orchesta Command Center.
"""
import os
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# ─── Shared Activity Log (injected by launch.py, or standalone fallback) ───
_standalone_log = []

def _get_activity_log():
    return _standalone_log

def _log_activity(source: str, text: str, direction: str = "in"):
    from datetime import datetime
    _standalone_log.insert(0, {
        "ts": datetime.now().isoformat(),
        "source": source,
        "direction": direction,
        "text": text[:300],
    })
    if len(_standalone_log) > 50:
        _standalone_log.pop()

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Orchesta Command Center API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent Registry
AGENTS = [
    {"id": "supervisor", "name": "Supervisor", "role": "Orchestrator", "icon": "🎯", "domain": "routing"},
    {"id": "academic", "name": "Academic Lead", "role": "Teaching & Student Success", "icon": "🎓", "domain": "academic"},
    {"id": "research", "name": "Research Scholar", "role": "PhD & Papers", "icon": "🔬", "domain": "research"},
    {"id": "tech", "name": "Coding Crew", "role": "Dev / Audit / Research", "icon": "💻", "domain": "tech"},
    {"id": "advisor", "name": "Strategic Advisor", "role": "Business Strategy", "icon": "♟️", "domain": "advisor"},
    {"id": "cos", "name": "Chief of Staff", "role": "Schedule & Ops", "icon": "📋", "domain": "cos"},
    {"id": "mimi", "name": "Mimi Tutor", "role": "Socratic Learning", "icon": "🧒", "domain": "mimi"},
    {"id": "wellness", "name": "Wellness Coach", "role": "Health & Mindset", "icon": "🧘", "domain": "wellness"},
    {"id": "heritage", "name": "Heritage Scholar", "role": "Philosophy & Culture", "icon": "📜", "domain": "heritage"},
    {"id": "legal", "name": "Legal Guardian", "role": "Law & Accounting", "icon": "⚖️", "domain": "legal"},
    {"id": "growth", "name": "Growth Specialist", "role": "Branding & Sales", "icon": "📈", "domain": "growth"},
    {"id": "bank", "name": "Bank Consultant", "role": "Banking & SME", "icon": "🏦", "domain": "bank"},
    {"id": "critic", "name": "Quality Guard", "role": "Output Validation", "icon": "🛡️", "domain": "quality"},
    {"id": "intel", "name": "Intel Officer", "role": "Synthesis Reports", "icon": "🕵️", "domain": "intelligence"},
]

LLM_PROVIDERS = [
    {"id": "gemini", "name": "Gemini Flash", "tier": "L2", "icon": "✨"},
    {"id": "groq", "name": "Groq (Llama3)", "tier": "L1", "icon": "⚡"},
    {"id": "zai", "name": "ZAI (GLM-5)", "tier": "L2", "icon": "🐲"},
    {"id": "deepseek", "name": "DeepSeek", "tier": "L3", "icon": "🔮"},
    {"id": "openrouter", "name": "OpenRouter", "tier": "L3", "icon": "🌐"},
    {"id": "local", "name": "Ollama (Local)", "tier": "L1", "icon": "🖥️"},
]


def _read_brain_md():
    """Reads BRAIN.md for recent memory entries."""
    brain_path = os.path.join(os.path.dirname(__file__), "../../BRAIN.md")
    try:
        with open(brain_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        memories = [l.strip() for l in lines if l.strip().startswith("- ")]
        return memories[-5:]  # Last 5 memories
    except:
        return []


def _read_heartbeat():
    """Reads HEARTBEAT.md for pending tasks."""
    hb_path = os.path.join(os.path.dirname(__file__), "../../HEARTBEAT.md")
    try:
        with open(hb_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tasks = [l.strip() for l in lines if l.strip().startswith("- [")]
        return tasks
    except:
        return []


def _check_api_health():
    """Reads 09_Executive_State_Hub for API key health."""
    hub_path = os.path.join(os.path.dirname(__file__), "../../09_Executive_State_Hub")
    try:
        with open(hub_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        failed = sum(1 for k in data if k.get("status") == "FAILED")
        total = len(data)
        return {"total_keys": total, "failed_keys": failed, "health_pct": round((1 - failed / total) * 100) if total > 0 else 0}
    except:
        return {"total_keys": 0, "failed_keys": 0, "health_pct": 100}


@app.get("/api/status")
def get_status():
    """Main status endpoint for the Command Center."""
    api_health = _check_api_health()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system_name": "Orchesta Assistant",
        "version": "Phase 15 — Command Center",
        "agents": AGENTS,
        "llm_providers": LLM_PROVIDERS,
        "api_health": api_health,
        "recent_memories": _read_brain_md(),
        "pending_tasks": _read_heartbeat(),
        "uptime_seconds": int(time.time()),
    }


from pydantic import BaseModel

class CommandRequest(BaseModel):
    command: str
    target_agent: str = "supervisor"

@app.get("/api/activity")
def get_activity():
    """Returns the shared activity log (Telegram + Dashboard commands)."""
    return {"activity": _get_activity_log()}

from typing import Dict, Any

class ManyChatRequest(BaseModel):
    user_id: str
    user_name: str
    message: str

@app.post("/api/webhook/manychat")
async def handle_manychat_webhook(request: ManyChatRequest):
    """
    Receives text messages from ManyChat via External Request.
    Returns a Dynamic Block formatted JSON for ManyChat to send back.
    """
    from core.services.chatbot_handler import chatbot
    
    _log_activity("manychat", f"👤 {request.user_name}: {request.message}", direction="in")
    
    try:
        reply = chatbot.handle_message(
            platform="facebook_messenger",
            user_id=request.user_id,
            user_name=request.user_name,
            message=request.message,
            metadata={"source": "manychat_dynamic_block"}
        )
        
        _log_activity("manychat", f"🤖 {reply[:200]}", direction="out")
        
        # ManyChat Dynamic Block Format
        return {
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": reply
                    }
                ]
            }
        }
    except Exception as e:
        print(f"  [Dashboard] ManyChat Webhook Error: {e}")
        return {
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": "Hệ thống AI đang bảo trì một chút, bạn đợi mình xíu nhé! 🙏"
                    }
                ]
            }
        }

@app.post("/api/command")
async def execute_command(request: CommandRequest):
    """Executes a command via the Supervisor Agent and logs it."""
    from core.agents.supervisor import build_supervisor_graph

    _log_activity("dashboard", f"👤 {request.command}", direction="in")
    print(f"  [Dashboard] Command from UI: {request.command}")

    try:
        graph = build_supervisor_graph()
        initial_state = {
            "messages": [request.command],
            "user_id": "dashboard_user",
            "retry_count": 0,
            "is_valid": True,
        }

        # Await the graph directly — uvicorn manages the event loop
        import asyncio
        result = await asyncio.wait_for(graph.ainvoke(initial_state), timeout=110.0)

        # Extract final answer
        final_answer = ""
        if result.get("messages"):
            for m in reversed(result["messages"]):
                msg_str = str(m)
                if msg_str.startswith(("System:", "Critic:", "Intel Agent:")):
                    continue
                final_answer = msg_str
                break

        if not final_answer:
            final_answer = "Đã xử lý nhưng không có phản hồi."

        _log_activity("dashboard", f"🤖 {final_answer[:200]}", direction="out")
        return {"status": "success", "response": final_answer, "timestamp": datetime.now().isoformat()}

    except asyncio.TimeoutError:
        err = "Agent timeout sau 90 giây."
        _log_activity("dashboard", f"⏱️ {err}", direction="out")
        return {"status": "error", "response": err, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        err = str(e)
        _log_activity("dashboard", f"❌ {err[:100]}", direction="out")
        return {"status": "error", "response": err, "timestamp": datetime.now().isoformat()}

# ─── Serve Dashboard UI (Must be the last route) ───
dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dashboard"))
if os.path.exists(dashboard_path):
    print(f"✅ Serving Dashboard from: {dashboard_path}")
    # Mount index.html at root
    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(dashboard_path, "index.html"))
    # Mount everything else at root
    app.mount("/", StaticFiles(directory=dashboard_path), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)

