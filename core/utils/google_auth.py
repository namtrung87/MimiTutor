import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from core.utils.bot_logger import get_logger

logger = get_logger("google_auth")
from googleapiclient.discovery import build

# Combined scopes for full ecosystem integration
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

class GoogleAuthManager:
    def __init__(self, credentials_path=None, token_path=None):
        self.base_path = r"E:\Drive\Antigravitiy\Orchesta assistant"
        self.credentials_path = credentials_path or os.path.join(self.base_path, "skills", "google_calendar", "credentials.json")
        self.token_path = token_path or os.path.join(self.base_path, "skills", "google_calendar", "token_unified.json")
        self.creds = None

    def get_credentials(self):
        """Gets valid user credentials from storage or initiates auth flow."""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}. Need re-authentication.")
                    self.creds = None
            
            if not self.creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Credentials file missing: {self.credentials_path}")
                
                # Use local server flow since OOB is deprecated
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, 
                    SCOPES
                )
                
                # We'll use a slightly more manual flow to ensure the URL is printed BEFORE blocking
                # but run_local_server is still the goal.
                print("\n" + "="*60)
                print("HỆ THỐNG YÊU CẦU XÁC THỰC GOOGLE")
                print("Trình duyệt sẽ tự động mở. Nếu không thấy, hãy click link dưới:")
                print("="*60 + "\n")
                
                # Run local server on a fixed port to avoid link confusion
                self.creds = flow.run_local_server(
                    host='localhost',
                    port=5050, 
                    authorization_prompt_message="Đang đợi xác thực tại: {url}",
                    success_message="Xác thực thành công! Bạn có thể đóng tab này.",
                    open_browser=True
                )

            # Save the credentials for the next run
            if self.creds:
                print(f"[*] Saving unified token to: {self.token_path}")
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            else:
                print("[!] Warning: Credentials object is None. Token not saved.")

        return self.creds

    def get_service(self, service_name, version):
        """Helper to build a Google API service."""
        creds = self.get_credentials()
        return build(service_name, version, credentials=creds)

if __name__ == "__main__":
    auth = GoogleAuthManager()
    try:
        creds = auth.get_credentials()
        print(f"Authenticated as: {creds.to_json()[:50]}...")
    except Exception as e:
        logger.error(f"Auth Flow failed: {e}")
