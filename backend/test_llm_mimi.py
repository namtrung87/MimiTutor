import os
import sys
from dotenv import load_dotenv

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../")) 
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Load env from backend
backend_env = os.path.join(current_dir, ".env")
load_dotenv(backend_env, override=True)

from core.utils.llm_manager import LLMManager

def test_llm():
    print("--- LLM Manager Diagnostic ---")
    manager = LLMManager(app_name="mimi_hometutor")
    
    # Check Providers
    print(f"Providers initialized: {[type(p).__name__ for p in manager.providers]}")
    
    test_prompt = "Chào em, em là ai?"
    print(f"\nTesting Query with prompt: '{test_prompt}'")
    
    try:
        response = manager.query(test_prompt, complexity="L1")
        if response:
            print(f"\nSUCCESS! Response: {response}")
        else:
            print("\nFAILURE: Manager returned None.")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_llm()
