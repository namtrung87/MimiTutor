import os
import sys
import io

# Force UTF-8 for console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Mock observability to avoid imports failing
# Mock observability/UsageStats to avoid imports failing
class MockObs:
    def start_trace(self, *args, **kwargs): return {}
    def end_trace(self, *args, **kwargs): pass
    def track_event(self, *args, **kwargs): pass

sys.modules['core.utils.observability'] = MockObs()
sys.modules['core.utils.llm_manager.UsageStats'] = MockObs()

from dotenv import load_dotenv
load_dotenv()

# Add project roots
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.append(current_dir)
sys.path.append(root_dir)

from core.utils.llm_manager import LLMManager, GeminiProvider, GroqProvider, NineRouterProvider

def audit():
    print("--- Mimi HomeTutor API Audit ---")
    print(f"Working Directory: {os.getcwd()}")
    
    manager = LLMManager(app_name="mimi_hometutor")
    
    # 1. Test Gemini
    print("\n[Audit] Testing Gemini Provider...")
    gemini = next((p for p in manager.providers if isinstance(p, GeminiProvider)), None)
    if gemini:
        res = gemini.query("Xin chào, bạn là ai?")
        if res:
            print(f"✅ Gemini Response: {res[:100]}...")
        else:
            print("❌ Gemini Failed (Check logs or API Key)")
    else:
        print("❗ Gemini Provider not initialized.")

    # 2. Test Groq
    print("\n[Audit] Testing Groq Provider...")
    groq = next((p for p in manager.providers if isinstance(p, GroqProvider)), None)
    if groq:
        res = groq.query("Xin chào, bạn là ai?")
        if res:
            print(f"✅ Groq Response: {res[:100]}...")
        else:
            print("❌ Groq Failed")
    else:
        print("❗ Groq Provider not initialized.")

    # 3. Test 9Router
    print("\n[Audit] Testing 9Router...")
    nine = next((p for p in manager.providers if isinstance(p, NineRouterProvider)), None)
    if nine:
        # Note: 9Router needs a local instance at 20128
        res = nine.query("Xin chào, bạn là ai?")
        if res:
            print(f"✅ 9Router Response: {res[:100]}...")
        else:
            print("❌ 9Router Failed (Is local 9Router running?)")
    else:
        print("❗ 9Router Provider not initialized.")

if __name__ == "__main__":
    audit()
