import requests
import os
import json
from dotenv import load_dotenv
from core.utils.error_logger import log_api_status

load_dotenv()

keys_str = os.getenv("ZAI_API_KEYS", "")
api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
model = os.getenv("ZAI_MODEL", "glm-4-plus")
api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

print(f"Starting API key audit for {len(api_keys)} keys...")

for i, key in enumerate(api_keys):
    key_prefix = key[:10]
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
        status_code = response.status_code
        if status_code == 200:
            status = "SUCCESS"
            error_msg = None
        else:
            status = "FAILED"
            error_msg = response.text
        
        log_api_status(key_prefix, status_code, status, error_msg)
        
    except Exception as e:
        log_api_status(key_prefix, 500, "ERROR", str(e))

print("Audit complete. Status hub updated.")
