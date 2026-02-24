import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

keys_str = os.getenv("ZAI_API_KEYS", "")
api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

models_to_test = ["GLM-5", "glm-4-plus"]
results = []

for key in api_keys:
    key_entry = {"key_prefix": key[:10], "results": {}}
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    for model in models_to_test:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            key_entry["results"][model] = {
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            key_entry["results"][model] = {"error": str(e)}
    
    results.append(key_entry)

with open("final_audit_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print("Final audit complete.")
