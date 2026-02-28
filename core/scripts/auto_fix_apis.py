import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Add project root to path
sys.path.append(r"E:\Drive\Antigravitiy\Orchesta assistant")

token_path = r"E:\Drive\Antigravitiy\Orchesta assistant\skills\google_calendar\token_unified.json"
backup_token_path = r"E:\Drive\Antigravitiy\Orchesta assistant\skills\google_calendar\token_backup.json"

def auto_fix_audit():
    print("--- PROACTIVE API AUDIT & AUTO-FIX ---")
    
    if not os.path.exists(token_path):
        print("[ERR] token_unified.json missing.")
        if os.path.exists(backup_token_path):
            print("[FIX] Found backup token. Restoring...")
            import shutil
            shutil.copy(backup_token_path, token_path)
            print("[FIX] Backup restored. Please re-run audit.")
            return
        else:
            print("[ERR] No backup found. Run 'python diag_auth.py' to re-authenticate.")
            return

    try:
        creds = Credentials.from_authorized_user_file(token_path)
    except Exception as e:
        print(f"[ERR] Token corrupted: {e}")
        return

    # Test Services
    services = [
        ('drive', 'v3', 'Google Drive'),
        ('gmail', 'v1', 'Gmail'),
        ('calendar', 'v3', 'Calendar')
    ]

    for service_key, version, label in services:
        print(f"\n[Audit] Testing {label}...")
        try:
            s_obj = build(service_key, version, credentials=creds)
            if service_key == 'drive':
                s_obj.files().list(pageSize=1).execute()
            elif service_key == 'gmail':
                s_obj.users().messages().list(userId='me', maxResults=1).execute()
            elif service_key == 'calendar':
                s_obj.calendarList().list().execute()
            print(f"    [OK] {label} is REACHABLE.")
        except Exception as e:
            msg = str(e).lower()
            print(f"    [FAIL] {label} FAILURE: {e}")
            
            if "expired" in msg or "refresh token" in msg:
                print(f"    [TIP] Suggestion: Token expired. Try running '/restart mimi-backend' to force refresh or re-auth.")
            elif "insufficient permission" in msg:
                print(f"    💡 Suggestion: OAuth scopes missing for {label}. Need to update GCP Project.")
            elif "403" in msg:
                print(f"    💡 Suggestion: API disabled in Google Cloud Console.")

if __name__ == "__main__":
    auto_fix_audit()
