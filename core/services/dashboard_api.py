"""
Phase 15: Dashboard Status API
Serves real-time system status for the Orchesta Command Center.
"""
import os
import json
import time
import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Depends, Security
from core.utils.api_auth import verify_api_key
from core.utils.bot_logger import get_logger

logger = get_logger("dashboard_api")

# ─── Shared Activity Log (injected by launch.py, or standalone fallback) ───
from core.utils.feature_flags import feature_flags
from core.utils.llm_config import llm_config
import traceback
from core.services.telegram_service import telegram_service
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
from fastapi.responses import FileResponse, HTMLResponse

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Orchesta Command Center API", version="1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# P0-2: Restrict CORS Origins
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8506").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Agent Registry
# Agent Registry (45 Skills across 4 Tactical Wings)
# Wings: ACADEMIC, CORPORATE, SYSTEM, PERSONAL
AGENTS = [
    # --- SUPERVISOR & METAMODELS ---
    {"id": "supervisor", "name": "Supervisor", "role": "Orchestrator", "icon": "🎯", "wing": "SYSTEM", "domain": "routing"},
    {"id": "critic", "name": "Quality Guard", "role": "Output Validation", "icon": "🛡️", "wing": "SYSTEM", "domain": "quality"},

    # --- ACADEMIC WING ---
    {"id": "academic", "name": "Academic Lead", "role": "PhD & Research Success", "icon": "🎓", "wing": "ACADEMIC", "domain": "academic"},
    {"id": "research", "name": "Research Scholar", "role": "Docx Engineering", "icon": "🔬", "wing": "ACADEMIC", "domain": "research"},
    {"id": "mimi", "name": "Mimi Tutor", "role": "Socratic Learning", "icon": "🧒", "wing": "ACADEMIC", "domain": "mimi"},
    {"id": "engineering", "name": "Academic Engineer", "role": "Doc Engineering", "icon": "📑", "wing": "ACADEMIC", "domain": "engineering"},
    {"id": "teacher", "name": "Master Teacher", "role": "PACE-X Strategy", "icon": "🍎", "wing": "ACADEMIC", "domain": "teaching"},
    {"id": "scholar", "name": "Uni Scholar", "role": "Advanced Modeling", "icon": "🏛️", "wing": "ACADEMIC", "domain": "scholar"},

    # --- CORPORATE WING ---
    {"id": "advisor", "name": "Strategic Advisor", "role": "Business & KTNB", "icon": "♟️", "wing": "CORPORATE", "domain": "advisor"},
    {"id": "cos", "name": "Chief of Staff", "role": "Executive Ops", "icon": "📋", "wing": "CORPORATE", "domain": "cos"},
    {"id": "legal", "name": "Legal Guardian", "role": "Law & Contracts", "icon": "⚖️", "wing": "CORPORATE", "domain": "legal"},
    {"id": "growth", "name": "Growth Specialist", "role": "Branding & Authority", "icon": "📈", "wing": "CORPORATE", "domain": "growth"},
    {"id": "bank", "name": "Bank Consultant", "role": "Banking & SME", "icon": "🏦", "wing": "CORPORATE", "domain": "bank"},
    {"id": "brand", "name": "Brand Architect", "role": "Content Pipelines", "icon": "🎨", "wing": "CORPORATE", "domain": "branding"},

    # --- SYSTEM WING ---
    {"id": "intel", "name": "Intel Officer", "role": "Synthesis Reports", "icon": "🕵️", "wing": "SYSTEM", "domain": "intelligence"},
    {"id": "medicine", "name": "Internal Med", "role": "System Recovery", "icon": "🩺", "wing": "SYSTEM", "domain": "repair"},
    {"id": "qa", "name": "QA Specialist", "role": "Regression Testing", "icon": "🧪", "wing": "SYSTEM", "domain": "testing"},
    {"id": "ethics", "name": "Policy Guard", "role": "Safety & Ethics", "icon": "🕊️", "wing": "SYSTEM", "domain": "compliance"},
    {"id": "memory", "name": "Semantic Memory", "role": "Hybrid Search", "icon": "🧠", "wing": "SYSTEM", "domain": "memory"},
    {"id": "synthesis", "name": "Deep Synthesis", "role": "NotebookLM Style", "icon": "📊", "wing": "SYSTEM", "domain": "synthesis"},
    {"id": "automation", "name": "N8N Automator", "role": "External Workflows", "icon": "⚙️", "wing": "SYSTEM", "domain": "automation"},
    {"id": "mcp", "name": "MCP Server", "role": "Standardized Tools", "icon": "🧩", "wing": "SYSTEM", "domain": "mcp"},
    {"id": "watchdog", "name": "Watchdog", "role": "Health Monitor", "icon": "🐕", "wing": "SYSTEM", "domain": "watchdog"},
    {"id": "tech", "name": "Coding Crew", "role": "Dev & Code", "icon": "💻", "wing": "SYSTEM", "domain": "tech"},

    # --- PERSONAL WING ---
    {"id": "wellness", "name": "Wellness Coach", "role": "Health & Habits", "icon": "🧘", "wing": "PERSONAL", "domain": "wellness"},
    {"id": "precision_health", "name": "Bio-Analytic", "role": "Biometric Trends", "icon": "⌚", "wing": "PERSONAL", "domain": "health"},
    {"id": "heritage", "name": "Heritage Scholar", "role": "Wisdom & Culture", "icon": "📜", "wing": "PERSONAL", "domain": "heritage"},
    {"id": "commute", "name": "Commute Insight", "role": "Voice Refinement", "icon": "🚌", "wing": "PERSONAL", "domain": "commute"},
    {"id": "trend", "name": "Trendscout", "role": "KOL Analysis", "icon": "🔥", "wing": "PERSONAL", "domain": "trend"},
    {"id": "learning", "name": "Personal Tutor", "role": "Learning logs", "icon": "📓", "wing": "PERSONAL", "domain": "learning"},
    {"id": "eq", "name": "EQ Sensing", "role": "Emotional Load", "icon": "💚", "wing": "PERSONAL", "domain": "eq"},
    {"id": "persona", "name": "Persona Shift", "role": "Tone & Style", "icon": "🎭", "wing": "PERSONAL", "domain": "persona"},
    {"id": "multimodal", "name": "Vision/Audio", "role": "Modal Extractor", "icon": "👁️", "wing": "PERSONAL", "domain": "multimodal"},
    {"id": "gamification", "name": "Game Strategist", "role": "Octalysis Loops", "icon": "🕹️", "wing": "PERSONAL", "domain": "gamification"},
    {"id": "iching", "name": "Kinh Dịch Expert", "role": "Divination & Feng Shui", "icon": "☯️", "wing": "PERSONAL", "domain": "iching"},
]

LLM_PROVIDERS = [
    {"id": "9router", "name": "9Router (Universal)", "tier": "Universal", "icon": "🚀"},
    {"id": "gemini", "name": "Gemini Flash", "tier": "L2", "icon": "✨"},
    {"id": "groq", "name": "Groq (Llama3)", "tier": "L1", "icon": "⚡"},
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
        if not os.path.exists(hub_path):
             return {"total_keys": 0, "failed_keys": 0, "health_pct": 100, "details": []}
        with open(hub_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        failed = sum(1 for k in data if k.get("status") == "FAILED")
        total = len(data)
        health_pct = round((1 - failed / total) * 100) if total > 0 else 100
        return {
            "total_keys": total, 
            "failed_keys": failed, 
            "health_pct": health_pct,
            "details": data[:10] # Top 10 for UI
        }
    except Exception as e:
        print(f"  [DashboardAPI] Error checking API health: {e}")
        return {"total_keys": 0, "failed_keys": 0, "health_pct": 100, "details": []}

def _get_token_stats():
    """Reads actual token usage and costs from usage_stats.json."""
    try:
        from core.utils.llm_manager import UsageStats
        stats = UsageStats.get_todays_stats()
        
        # Simplify for dashboard
        providers = {}
        for model, data in stats.get("models", {}).items():
            if not isinstance(data, dict): continue
            base = str(model).split("/")[-1].lower()
            if "gemini" in base: key = "gemini"
            elif "llama" in base or "groq" in base: key = "groq"
            elif "deepseek" in base: key = "deepseek"
            else: key = "other"
            
            providers[key] = providers.get(key, 0) + data.get("prompt", 0) + data.get("completion", 0)

        return {
            "daily_usage": sum(providers.values()),
            "daily_cost_vnd": stats.get("total_cost_vnd", 0),
            "providers": providers or {"gemini": 0, "groq": 0}
        }
    except Exception as e:
        print(f"  [DashboardAPI] Error in _get_token_stats: {e}")
        return {"daily_usage": 0, "daily_cost_vnd": 0, "providers": {"gemini": 0}}

def _get_routing_rules():
    """Reads routing_config.json to expose the LLM Rules of Engagement."""
    config_path = os.path.join(os.path.dirname(__file__), "../../core/utils/routing_config.json")
    try:
        if not os.path.exists(config_path):
            return {}
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [DashboardAPI] Error loading routing rules: {e}")
        return {}

def _get_task_hierarchy():
    """Returns a simplified map of the supervisor workflow for visualization."""
    return {
        "entry": "ops_guard",
        "flow": [
            {"from": "ops_guard", "to": "eq_sensing"},
            {"from": "eq_sensing", "to": "readiness_check"},
            {"from": "readiness_check", "to": "memory_retrieval"},
            {"from": "memory_retrieval", "to": "supervisor"},
            {"from": "supervisor", "to": "specialized_agents", "type": "routing"},
            {"from": "specialized_agents", "to": "token_tracker"},
            {"from": "token_tracker", "to": "critic"},
            {"from": "critic", "to": "END"}
        ],
        "agent_wings": {
            "ACADEMIC": ["academic", "research", "mimi", "teaching"],
            "CORPORATE": ["advisor", "cos", "legal", "growth", "bank"],
            "SYSTEM": ["intel", "medicine", "qa", "ethics", "memory", "tech"],
            "PERSONAL": ["wellness", "heritage", "trend", "iching"]
        }
    }

def _get_system_metrics():
    """Get real-time CPU and RAM usage."""
    try:
        process = psutil.Process(os.getpid())
        return {
            "cpu_pct": psutil.cpu_percent(),
            "ram_mb": round(process.memory_info().rss / (1024 * 1024), 1),
            "ram_pct": psutil.virtual_memory().percent,
            "threads": process.num_threads(),
            "uptime": int(time.time() - process.create_time())
        }
    except Exception as e:
        print(f"  [DashboardAPI] Error getting system metrics: {e}")
        return {"cpu_pct": 0, "ram_mb": 0, "ram_pct": 0, "threads": 0, "uptime": 0}


@app.get("/api/status")
def get_status():
    """Main status endpoint for the Command Center. Wrapped in global try-except for stability."""
    try:
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
            "features": feature_flags.get_all(),
            "token_stats": _get_token_stats(),
            "system_metrics": _get_system_metrics(),
            "task_hierarchy": _get_task_hierarchy(),
            "routing_rules": _get_routing_rules(),
            "uptime_seconds": int(time.time()),
            "status": "online"
        }
    except Exception as e:
        print(f"  [DashboardAPI] CRITICAL ERROR in get_status: {e}")
        traceback.print_exc()
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "partial_error",
            "error_detail": str(e),
            "agents": AGENTS,
            "llm_providers": LLM_PROVIDERS
        }


from pydantic import BaseModel

class CommandRequest(BaseModel):
    command: str
    target_agent: str = "supervisor"

@app.get("/api/metrics")
def get_metrics():
    """Returns real-time system metrics."""
    return _get_system_metrics()

@app.get("/api/activity")
def get_activity():
    """Returns the shared activity log (Telegram + Dashboard commands)."""
    return {"activity": _get_activity_log()}

from typing import Dict, Any

class ManyChatRequest(BaseModel):
    user_id: str
    user_name: str
    message: str

class AppleHealthRequest(BaseModel):
    date: str
    time_asleep_hrs: float
    time_in_bed_hrs: float

class FeatureToggleRequest(BaseModel):
    feature: str
    enabled: bool

class LLMToggleRequest(BaseModel):
    app_name: str
    provider: str
    enabled: bool

@app.get("/api/features")
def get_features():
    """Returns all current feature flags."""
    return feature_flags.get_all()

@app.post("/api/features/toggle", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def toggle_feature(request: FeatureToggleRequest):
    """Toggles a feature state."""
    feature_flags.set_feature(request.feature, request.enabled)
    _log_activity("dashboard", f"⚙️ Feature '{request.feature}' set to {request.enabled}", direction="in")
    return {"status": "success", "feature": request.feature, "enabled": request.enabled}

@app.get("/api/llm-config")
def get_llm_config():
    """Returns the full LLM configuration (app/provider toggles)."""
    return llm_config.get_all()

@app.post("/api/llm-config/toggle", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def toggle_llm_provider(request: LLMToggleRequest):
    """Toggles a specific LLM provider for an app."""
    llm_config.set_provider_status(request.app_name, request.provider, request.enabled)
    _log_activity("dashboard", f"🤖 LLM '{request.provider}' for '{request.app_name}' set to {request.enabled}", direction="in")
    return {"status": "success", "app_name": request.app_name, "provider": request.provider, "enabled": request.enabled}

@app.post("/api/webhook/manychat")
@limiter.limit("30/minute")
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
        logger.error(f"ManyChat Webhook Error: {e}")
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

@app.post("/api/webhook/apple_health")
@limiter.limit("10/minute")
async def handle_apple_health_webhook(request: AppleHealthRequest):
    """
    Receives daily sleep data from Apple Watch via Apple Shortcuts automation.
    """
    _log_activity("apple_health", f"⌚ Nhận dữ liệu giấc ngủ: {request.time_asleep_hrs}h / {request.time_in_bed_hrs}h", direction="in")
    
    try:
        data_dir = os.path.join(os.path.dirname(__file__), "../../../data")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "apple_health.json")
        
        # Load existing data
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    history = []
        else:
            history = []
            
        # Add new entry
        entry = {
            "date": request.date,
            "time_asleep_hrs": request.time_asleep_hrs,
            "time_in_bed_hrs": request.time_in_bed_hrs,
            "timestamp": datetime.now().isoformat()
        }
        
        # Avoid duplicate dates
        history = [h for h in history if h.get("date") != request.date]
        history.append(entry)
        
        # Build prompt for telegram bot / wellness agent context
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
            
        # Proactively notify the user via Telegram
        try:
            from core.agents.wellness_agent import WellnessAgent
            agent = WellnessAgent()
            # Explicitly request advice based on the new data
            prompt = f"Tôi vừa ngủ dậy. Đây là dữ liệu giấc ngủ: {request.time_asleep_hrs}h (trong đó nằm giường {request.time_in_bed_hrs}h). Hãy phân tích và cho tôi lời khuyên về năng lượng và việc tập luyện MMA/Coding hôm nay."
            
            # Using asyncio.create_task to not block the webhook response
            async def proactive_advice():
                advice = await asyncio.to_thread(agent.process_request, prompt)
                msg = f"⌚ *Apple Watch Sync:* {request.time_asleep_hrs}h Sleep\n\n{advice}"
                await telegram_service.send_message(msg)
            
            asyncio.create_task(proactive_advice())
        except Exception as e:
            logger.error(f"Proactive advice error: {e}")
            
        return {"status": "success", "message": "Sleep data stored and advice triggered"}
    except Exception as e:
        _log_activity("apple_health", f"❌ Error saving sleep data: {str(e)[:100]}", direction="out")
        return {"status": "error", "message": str(e)}

@app.post("/api/command", dependencies=[Depends(verify_api_key)])
@limiter.limit("15/minute")
async def execute_command(request: CommandRequest):
    """Executes a command via the Supervisor Agent and logs it."""
    _log_activity("dashboard", f"👤 {request.command}", direction="in")
    print(f"  [Dashboard] Command from UI: {request.command}")

    try:
        from core.agents.supervisor import build_supervisor_graph
        graph = build_supervisor_graph()
        initial_state = {
            "messages": [request.command],
            "user_id": "dashboard_user",
            "retry_count": 0,
            "is_valid": True,
        }

        # Await the graph directly — uvicorn manages the event loop
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
        traceback.print_exc()
        err = f"Lỗi hệ thống: {str(e)}"
        _log_activity("dashboard", f"❌ {err[:100]}", direction="out")
        return {"status": "error", "response": err, "timestamp": datetime.now().isoformat()}

# ─── Serve Kinh Dich App ───
kinh_dich_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../kinh_dich_app"))
if os.path.exists(kinh_dich_path):
    print(f"OK Serving Kinh Dich App Assets from: {kinh_dich_path}")
    # Mount assets first
    app.mount("/iching-assets", StaticFiles(directory=kinh_dich_path), name="iching_assets")
    
    @app.get("/iching")
    async def read_iching_index():
        with open(os.path.join(kinh_dich_path, "index.html"), "r", encoding="utf-8") as f:
            content = f.read()
        # Rewrite paths dynamically to use the mounted assets
        content = content.replace('href="style.css"', 'href="/iching-assets/style.css"')
        content = content.replace('src="data.js"', 'src="/iching-assets/data.js"')
        content = content.replace('src="app.js"', 'src="/iching-assets/app.js"')
        return HTMLResponse(content=content)

# ─── Serve Dashboard UI (Must be the last route) ───
dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dashboard"))
if os.path.exists(dashboard_path):
    print(f"OK Serving Dashboard from: {dashboard_path}")
    # Mount index.html at root
    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(dashboard_path, "index.html"))
    # Mount everything else at root
    app.mount("/", StaticFiles(directory=dashboard_path), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8506)

