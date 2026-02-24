from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sys
import io

# Add current and parent directory to sys.path for robust imports in Linux/Render
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../")) # 05_Mimi_HomeTutor
true_root = os.path.abspath(os.path.join(root_dir, "../"))    # Project Root

for path in [root_dir, true_root]:
    if path not in sys.path:
        sys.path.append(path)

# Ensure UTF-8 for logs
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from core.agents.mimi_hometutor import build_mimi_graph
from core.state import AgentState
from core.utils.multimodal_extractor import MultimodalExtractor
import tempfile
import shutil

extractor = MultimodalExtractor()

app = FastAPI(title="Mimi Socratic API")

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

class ChatResponse(BaseModel):
    response: str

graph = build_mimi_graph()

import traceback

@app.post("/mimi/chat", response_model=ChatResponse)
async def mimi_chat(request: ChatRequest):
    initial_state = {
        "messages": [f"Mimi: {request.message}"], # Prefix to force routing
        "user_id": request.user_id,
        "input_file": "",
        "file_content": None,
        "extracted_skill": None,
        "skill_saved": False,
        "routing_category": "mimi"
    }
    
    try:
        results = graph.invoke(initial_state)
        messages = results.get("messages", [])
        
        print(f"DEBUG: Full messages list: {messages}", flush=True)
        
        # Search backwards for the last pedagogical or user message
        response_text = "I'm sorry, I couldn't generate a response."
        # Known prefixes for actual content
        agent_prefixes = ("Mimi Agent:", "Scholar Agent:", "Academic Agent:", "Socratic Agent:", "Tutor Agent:", "Mimi:", "Scholar:")
        
        for msg in reversed(messages):
            print(f"DEBUG: Evaluating message: {msg}", flush=True)
            if msg and isinstance(msg, str):
                msg_clean = msg.strip()
                # Skip system messages
                if msg_clean.startswith("System:"):
                    continue
                
                # If it's an agent response with a known prefix, extract the content
                for prefix in agent_prefixes:
                    if msg_clean.startswith(prefix):
                        response_text = msg_clean.split(prefix, 1)[-1].strip()
                        print(f"DEBUG: Selected agent response: {response_text}", flush=True)
                        return ChatResponse(response=response_text)
                
                # Fallback: if no prefix matches but it's not a system message, 
                # we check if it looks like a verdict (to skip it)
                if any(v in msg_clean for v in ["APPROVE | Reason", "REVISE | Reason"]):
                    print(f"DEBUG: Skipping internal verdict: {msg_clean}", flush=True)
                    continue
                    
                # Last resort: return the raw message if it's not system-like
                response_text = msg_clean
                print(f"DEBUG: Selected raw response: {response_text}", flush=True)
                break
        
        return ChatResponse(response=response_text)
    except Exception as e:
        print(f"Error in mimi_chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
    file: Optional[UploadFile] = File(None)
):
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
        "input_file": "",
        "file_content": None,
        "extracted_skill": None,
        "skill_saved": False,
        "routing_category": "mimi"
    }
    
    try:
        results = graph.invoke(initial_state)
        messages = results.get("messages", [])
        print(f"  [Multimodal API] Graph Messages: {messages}")
        
        response_text = "I'm sorry, I couldn't generate a response."
        agent_prefixes = ("Mimi Agent:", "Scholar Agent:", "Academic Agent:", "Socratic Agent:", "Tutor Agent:", "Summarize Agent:")
        
        for msg in reversed(messages):
            if msg and isinstance(msg, str):
                msg_clean = msg.strip()
                if msg_clean.startswith("System:") or msg_clean.startswith("Mimi:"):
                    continue
                
                # Check for agent prefixes
                found_prefix = False
                for prefix in agent_prefixes:
                    if msg_clean.startswith(prefix):
                        response_text = msg_clean.split(prefix, 1)[-1].strip()
                        found_prefix = True
                        break
                
                if found_prefix:
                    return ChatResponse(response=response_text)
                
                if any(v in msg_clean for v in ["APPROVE | Reason", "REVISE | Reason"]):
                    continue
                
                response_text = msg_clean
                break
        
        return ChatResponse(response=response_text)
    except Exception as e:
        print(f"Error in mimi_chat_multimodal: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    # Diagnostic: Print folder structure
    print(f"  [Startup] CWD: {os.getcwd()}")
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        print(f"  [Startup] Repo Root: {repo_root}")
        print(f"  [Startup] Files in Root: {os.listdir(repo_root)}")
        if os.path.exists(os.path.join(repo_root, "materials")):
            print(f"  [Startup] Materials found in Root: {os.listdir(os.path.join(repo_root, 'materials'))}")
    except Exception as e:
        print(f"  [Startup] Diagnostic error: {e}")

    # Automatically sync Mimi Science material if present in materials folder
    try:
        from core.agents.policy_agent import KnowledgeAgent
        agent = KnowledgeAgent()
        print("  [Startup] Checking for Science materials...")
        count = agent.sync_mimi_learning()
        if count > 0:
            print(f"  [Startup] Knowledge Base updated with {count} science segments.")
        else:
            print("  [Startup] No new science materials indexed.")
    except Exception as e:
        print(f"  [Startup] Sync failed: {e}")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
