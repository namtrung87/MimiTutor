import os
import sys
from dotenv import load_dotenv

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.utils.llm_manager import LLMManager

def test_llms():
    manager = LLMManager()
    print(f"Initialized providers: {[type(p).__name__ for p in manager.providers]}")
    
    test_prompt = "Hello, are you working? Respond with 'Yes'."
    
    for provider in manager.providers:
        print(f"Testing {type(provider).__name__}...")
        try:
            res = provider.query(test_prompt)
            if res:
                print(f"  [SUCCESS] {type(provider).__name__}: {res[:30]}")
            else:
                print(f"  [FAILED] {type(provider).__name__}: Returned None")
        except Exception as e:
            print(f"  [ERROR] {type(provider).__name__}: {e}")

if __name__ == "__main__":
    load_dotenv()
    test_llms()
