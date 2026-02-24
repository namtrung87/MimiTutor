import requests
import os
from dotenv import load_dotenv

load_dotenv()

keys_str = os.getenv("ZAI_API_KEYS", "")
api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
model = os.getenv("ZAI_MODEL", "glm-4-plus")
api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

if not api_keys:
    print("No keys found!")
    exit(1)

key = api_keys[0]
print(f"Testing key: {key[:10]}...")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

try:
    response = requests.post(api_url, headers=headers, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
