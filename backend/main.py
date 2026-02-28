from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import io
import asyncio

# Add current and parent directory to sys.path for robust imports in Linux/Render
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../")) # 05_Mimi_HomeTutor
true_root = os.path.abspath(os.path.join(root_dir, "../"))    # Project Root

# Prioritize project root and local root in sys.path
# We want: [true_root, root_dir, ...]
# Only remove the source roots if they are already in path to avoid duplicates, 
# but DO NOT remove the entire .venv_fix site-packages.
for p in [root_dir, true_root]:
    if p in sys.path:
        sys.path.remove(p)
sys.path.insert(0, root_dir)
sys.path.insert(0, true_root)

print(f"DEBUG: sys.path[0] = {sys.path[0]}", flush=True)
print(f"DEBUG: sys.path[1] = {sys.path[1]}", flush=True)

# Ensure UTF-8 for logs on Windows to prevent Errno 22
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from core.agents.mimi_hometutor import build_mimi_graph
from core.state import AgentState
from core.utils.multimodal_extractor import MultimodalExtractor
import tempfile
import shutil

extractor = MultimodalExtractor()

app = FastAPI(title="Mimi Socratic API")

# Vietnamese fallback message shown as a normal bot reply when the LLM chain fails.
# Returning HTTP 200 here prevents the frontend catch block from firing.
MIMI_FALLBACK_MSG = (
    "Ối, chị bị đứt dòng suy nghĩ một chút rồi! 🌸 "
    "Em hỏi lại chị câu đó nhé, chị sẽ cố gắng trả lời ngay!"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Mimi Socratic API is online!",
        "version": "1.1.2",
        "endpoints": ["/mimi/chat", "/health", "/mimi/chat/multimodal"]
    }

print(f"MIMI_BACKEND_VERSION: 1.1.2 - MIMI_GRAPH_DEPLOYED - ROOT: {root_dir}", flush=True)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[str]] = []
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = "default_session"

class ChatResponse(BaseModel):
    response: str

class FeedbackRequest(BaseModel):
    session_id: str
    message_index: int
    rating: int # 1 for up, -1 for down

# Rate Limiting
import time
RATE_LIMIT_DICT = {}
MAX_REQUESTS_PER_MIN = 10

def check_rate_limit(identifier: str):
    """Simple sliding window rate limiter."""
    now = time.time()
    if identifier not in RATE_LIMIT_DICT:
        RATE_LIMIT_DICT[identifier] = []
    
    # Filter out requests older than 60 seconds
    RATE_LIMIT_DICT[identifier] = [req_time for req_time in RATE_LIMIT_DICT[identifier] if now - req_time < 60]
    
    if len(RATE_LIMIT_DICT[identifier]) >= MAX_REQUESTS_PER_MIN:
        raise HTTPException(status_code=429, detail="Bạn hỏi hơi nhanh rồi đó! Nghỉ tay 1 phút rồi quay lại nha Mimi! 🌸")
        
    RATE_LIMIT_DICT[identifier].append(now)

graph = build_mimi_graph()

import traceback

def extract_final_response(results: dict) -> str:
    """
    Robustly extracts the final response from the agent graph results.
    Prioritizes the 'final_response' field, then falls back to prefix scanning.
    """
    if not results:
        return "Chị chưa nhận được câu trả lời phù hợp. Em hỏi lại chị theo cách khác được không? 🌸"
    
    # 1. First priority: Check the dedicated field
    final_resp = results.get("final_response")
    if final_resp and isinstance(final_resp, str):
        print(f"DEBUG: Found final_response field: {final_resp[:100]}...", flush=True)
        return final_resp.strip()
    
    # 2. Fallback: Scan messages backwards for agent prefixes
    messages = results.get("messages", [])
    agent_prefixes = ("Mimi Agent:", "Scholar Agent:", "Academic Agent:", "Socratic Agent:", "Tutor Agent:", "Summarize Agent:", "Mimi:", "Scholar:")
    
    for msg in reversed(messages):
        if msg and isinstance(msg, str):
            msg_clean = msg.strip()
            # Skip system messages and internal verdicts
            if msg_clean.startswith("System:") or any(v in msg_clean for v in ["APPROVE | Reason", "REVISE | Reason"]):
                continue
            
            # check for prefixes
            for prefix in agent_prefixes:
                if msg_clean.startswith(prefix):
                    extracted = msg_clean.split(prefix, 1)[-1].strip()
                    print(f"DEBUG: Extracted via prefix '{prefix}': {extracted[:100]}...", flush=True)
                    return extracted
            
            # If no prefix match but it's not system-like, return it as raw response
            print(f"DEBUG: Falling back to raw message: {msg_clean[:100]}...", flush=True)
            return msg_clean

    return "Chị chưa nhận được câu trả lời phù hợp. Em hỏi lại chị theo cách khác được không? 🌸"

@app.post("/mimi/chat", response_model=ChatResponse)
async def mimi_chat(request: ChatRequest):
    check_rate_limit(request.session_id or request.user_id)
    
    initial_state = {
        "messages": [f"Mimi: {request.message}"], # Prefix to force routing
        "user_id": request.user_id,
        "session_id": request.session_id,
        "input_file": "",
        "file_content": None,
        "extracted_skill": None,
        "skill_saved": False,
        "routing_category": "mimi"
    }
    
    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(graph.invoke, initial_state), 
            timeout=60.0
        )
        response_text = extract_final_response(results)
        return ChatResponse(response=response_text)
    except asyncio.TimeoutError:
        print("Timeout in mimi_chat after 60.0s")
        return ChatResponse(response=MIMI_FALLBACK_MSG)
    except Exception as e:
        print(f"Error in mimi_chat: {e}")
        traceback.print_exc()
        # Return HTTP 200 with warm Vietnamese fallback — never expose a 500 to the frontend
        return ChatResponse(response=MIMI_FALLBACK_MSG)

@app.post("/parent/report", response_model=ChatResponse)
async def parent_report(request: ChatRequest):
    # Here we can force routing to the reporting agent
    initial_state = {
        "messages": ["Parent: Generate report"], 
        "input_file": "",
        "file_content": None,
        "extracted_skill": None,
        "skill_saved": False,
        "routing_category": "academic"
    }
    
    try:
        results = graph.invoke(initial_state)
        messages = results.get("messages", [])
        
        response_text = "I'm sorry, I couldn't generate a report."
        for msg in reversed(messages):
            if msg and isinstance(msg, str) and not msg.startswith("System:"):
                response_text = msg
                break
                
        return ChatResponse(response=response_text)
    except Exception as e:
        print(f"Error in parent_report: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mimi/chat/multimodal", response_model=ChatResponse)
async def mimi_chat_multimodal(
    message: str = Form(""),
    user_id: str = Form("default_user"),
    session_id: str = Form("default_session"),
    file: Optional[UploadFile] = File(None)
):
    check_rate_limit(session_id or user_id)
    
    final_message = message

    if file:
        try:
            suffix = os.path.splitext(file.filename)[1] if file.filename else ""
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_path = temp_file.name
            
            # Process with Gemini
            extracted_text = extractor.process_file(temp_path, mime_type=file.content_type)
            os.unlink(temp_path)
            
            if final_message:
                final_message += f"\n\n[Đính kèm đa phương tiện]: {extracted_text}"
            else:
                final_message = f"[Voice/Ảnh tải lên]: {extracted_text}"
                
        except Exception as e:
            print(f"Error processing upload: {e}")
            raise HTTPException(status_code=400, detail="Could not process uploaded file")
            
    if not final_message.strip():
         final_message = "(Nhạc/Hình không có nội dung rõ ràng)"

    initial_state = {
        "messages": [f"Mimi: {final_message}"],
        "user_id": user_id,
        "session_id": session_id,
        "input_file": "",
        "file_content": None,
        "extracted_skill": None,
        "skill_saved": False,
        "routing_category": "mimi"
    }
    
    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(graph.invoke, initial_state), 
            timeout=60.0
        )
        response_text = extract_final_response(results)
        return ChatResponse(response=response_text)
    except asyncio.TimeoutError:
        print("Timeout in mimi_chat_multimodal after 60.0s")
        return ChatResponse(response=MIMI_FALLBACK_MSG)
    except Exception as e:
        print(f"Error in mimi_chat_multimodal: {e}")
        traceback.print_exc()
        return ChatResponse(response=MIMI_FALLBACK_MSG)

@app.on_event("startup")
async def startup_event():
    # Diagnostic: Print folder structure
    print(f"  [Startup] CWD: {os.getcwd()}")
    import asyncio
    
    def sync_task():
        try:
            from core.agents.policy_agent import KnowledgeAgent
            agent = KnowledgeAgent()
            print("  [Startup] Syncing Mimi Science materials (async)...")
            count = agent.sync_mimi_learning()
            print(f"  [Startup] Knowledge Base updated with {count} segments.")
        except Exception as e:
            print(f"  [Startup] Sync failed: {e}")
            
    # Run synchronously blocking operations in a thread pool non-blocking the FastAPI event loop
    asyncio.create_task(asyncio.to_thread(sync_task))

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/mimi/sync")
async def manual_sync():
    try:
        from core.agents.policy_agent import KnowledgeAgent
        agent = KnowledgeAgent()
        count = agent.sync_mimi_learning()
        return {"status": "success", "ingested": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mimi/feedback")
async def mimi_feedback(request: FeedbackRequest):
    # Log feedback for analytics/review
    # In a fully persistent system, this would write to a DB
    icon = "👍" if request.rating > 0 else "👎"
    print(f"  [Feedback] {icon} Session: {request.session_id} | Msg Index: {request.message_index}")
    return {"status": "success", "recorded": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
