import os
import sys
import traceback
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate():
    print("--- GOOGLE CALENDAR AUTHENTICATION (CONSOLE FLOW) ---")
    
    base_path = r"E:\Drive\Antigravitiy\Orchesta assistant"
    creds_path = os.path.join(base_path, "skills", "google_calendar", "credentials.json")
    token_path = os.path.join(base_path, "skills", "google_calendar", "token.json")

    if not os.path.exists(creds_path):
        print(f"Error: {creds_path} not found.")
        return

    try:
        # We use a flow that requires the user to copy-paste a code
        flow = InstalledAppFlow.from_client_secrets_file(
            creds_path, 
            SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        with open(os.path.join(base_path, "skills", "google_calendar", "auth_url.txt"), 'w') as f:
            f.write(auth_url)
            
        print("\n" + "="*60)
        print("BƯỚC 1: Hãy copy link trong file auth_url.txt hoặc link dưới đây:")
        print(auth_url)
        print("="*60 + "\n")
        
        print("BƯỚC 2: Sau khi đăng nhập, Google sẽ cung cấp một MÃ XÁC THỰC (Authorization Code).")
        print("Hãy copy mã đó và dán vào đây.")
        
        # This is a bit manual but extremely reliable
        code = input("Nhập mã xác thực của bạn: ").strip()
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
        print(f"\n[SUCCESS] token.json đã được tạo tại {token_path}")
        
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    authenticate()
