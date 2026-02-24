import requests
import os
from dotenv import load_dotenv

load_dotenv()

keys_str = os.getenv("ZAI_API_KEYS", "")
api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
model = os.getenv("ZAI_MODEL", "glm-4-flash")
api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

print(f"Checking {len(api_keys)} keys for model {model}...")

for i, key in enumerate(api_keys):
    print(f"[{i}] Key {key[:10]}... ", end="", flush=True)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print("OK")
        else:
            print(f"FAILED ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
