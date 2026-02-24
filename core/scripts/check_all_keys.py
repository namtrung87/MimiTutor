import requests
import os
from dotenv import load_dotenv

load_dotenv()

keys_str = os.getenv("ZAI_API_KEYS", "")
api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
model = os.getenv("ZAI_MODEL", "glm-4-plus")
api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

print(f"--- Auditing {len(api_keys)} Z.ai API Keys ---")

for i, key in enumerate(api_keys):
    print(f"\n[{i+1}] Testing Key: {key[:10]}...")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"    STATUS: SUCCESS (200 OK)")
        else:
            print(f"    STATUS: FAILED ({response.status_code})")
            print(f"    RESPONSE: {response.text}")
    except Exception as e:
        print(f"    ERROR: {str(e)}")

print("\n--- Audit Complete ---")
