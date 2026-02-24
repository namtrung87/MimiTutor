import json
import os
from datetime import datetime

STATE_HUB_PATH = r"c:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\09_Executive_State_Hub"

def log_api_status(key_prefix, status_code, status, error_message=None):
    """
    Logs or updates the status of an API key in the Executive State Hub.
    """
    try:
        if os.path.exists(STATE_HUB_PATH):
            with open(STATE_HUB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []

        # Find existing entry or create new
        found = False
        for entry in data:
            if entry.get("key_prefix") == key_prefix:
                entry["status_code"] = status_code
                entry["status"] = status
                entry["error_message"] = error_message
                entry["last_updated"] = datetime.now().isoformat()
                found = True
                break
        
        if not found:
            data.append({
                "index": len(data) + 1,
                "key_prefix": key_prefix,
                "status_code": status_code,
                "status": status,
                "error_message": error_message,
                "last_updated": datetime.now().isoformat()
            })

        with open(STATE_HUB_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"Logged status for {key_prefix}: {status}")
    except Exception as e:
        print(f"Failed to log API status: {e}")

if __name__ == "__main__":
    # Test logging
    log_api_status("test_prefix", 200, "SUCCESS")
