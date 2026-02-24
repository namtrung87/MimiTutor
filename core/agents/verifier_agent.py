import os
import subprocess
import re
import tempfile
from typing import Optional, Dict, Any
from core.state import AgentState

class VerifierAgent:
    """
    Verifier Agent:
    Responsible for extracting code from agent responses,
    executing it in a safe (local) environment, and capturing feedback.
    """
    def __init__(self):
        pass

    def extract_code(self, text: Optional[str]) -> Optional[str]:
        """Extracts the first Python code block found in the text."""
        if not text:
            return None
        pattern = r"```python\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback for generic code blocks if python is not specified but content looks like python
        pattern_generic = r"```\n(.*?)```"
        match_generic = re.search(pattern_generic, text, re.DOTALL)
        if match_generic:
            return match_generic.group(1).strip()
            
        return None

    def run_code(self, code: str) -> Dict[str, Any]:
        """Runs the provided code in a subprocess and captures output."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # Set PYTHONPATH to include current directory for local imports
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
            
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=30, # 30s timeout for safety
                env=env
            )
            
            logs = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            status = "success" if result.returncode == 0 else "failure"
            
            return {
                "status": status,
                "logs": logs.strip(),
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "failure",
                "logs": "Execution timed out after 30 seconds.",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "status": "failure",
                "logs": f"Internal Verifier Error: {str(e)}",
                "exit_code": -1
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def verifier_node(state: AgentState):
    """
    LangGraph node for runtime verification.
    """
    verifier = VerifierAgent()
    
    # We look for code in the most recent AI message or developer_output
    # Priority: developer_output (if in tech flow) -> last message
    text_to_verify = state.get("developer_output")
    if not text_to_verify and state.get("messages"):
        text_to_verify = state["messages"][-1]
        
    if not text_to_verify:
        return {"execution_status": "pending", "verification_logs": "No code found to verify."}

    code = verifier.extract_code(text_to_verify)
    if not code:
        print("  [Verifier] No Python code block found to execute.")
        return {"execution_status": "pending", "verification_logs": "No Python code blocks detected."}

    print(f"  [Verifier] Executing code (len={len(code)})...")
    result = verifier.run_code(code)
    
    print(f"  [Verifier] Result: {result['status']}")
    
    # Update state
    return {
        "execution_status": result["status"],
        "verification_logs": result["logs"]
    }
