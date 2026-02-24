import os
import re
import json
import subprocess
import sys
from pathlib import Path

# Configuration
COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
STATE_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\account_states.json")
UV_PATH = Path(r"C:\Users\Trung Nguyen\.local\bin\uv.exe")

class NotebookManager:
    def __init__(self):
        self.accounts = self._load_accounts()
        self.state = self._load_state()

    def _load_accounts(self):
        accounts = []
        if not COOKIES_DIR.exists():
            print(f"Error: Cookies directory not found at {COOKIES_DIR}")
            return accounts

        for cookie_file in COOKIES_DIR.glob("*.txt"):
            session_id = None
            papisid = None
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if "__Secure-1PSID" in line:
                            parts = line.split("\t")
                            if len(parts) >= 7:
                                session_id = parts[6].strip()
                        if "__Secure-1PAPISID" in line:
                            parts = line.split("\t")
                            if len(parts) >= 7:
                                papisid = parts[6].strip() or parts[5].strip() # Fallback for some formats
                
                if session_id and papisid:
                    accounts.append({
                        "id": cookie_file.name,
                        "session_id": session_id,
                        "papisid": papisid
                    })
            except Exception as e:
                print(f"Warning: Failed to parse {cookie_file}: {e}")
        
        return accounts

    def _load_state(self):
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {"current_index": 0, "full_accounts": []}

    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def get_current_account(self):
        if not self.accounts:
            return None
        
        idx = self.state.get("current_index", 0)
        if idx >= len(self.accounts):
            idx = 0
            self.state["current_index"] = 0
        
        return self.accounts[idx]

    def rotate_account(self):
        if not self.accounts:
            return False
        
        current_idx = self.state.get("current_index", 0)
        # Mark current as full for a while (conceptually)
        account_id = self.accounts[current_idx]["id"]
        if account_id not in self.state["full_accounts"]:
            self.state["full_accounts"].append(account_id)
        
        # Move to next
        next_idx = (current_idx + 1) % len(self.accounts)
        self.state["current_index"] = next_idx
        self._save_state()
        print(f"Rotating to account: {self.accounts[next_idx]['id']}")
        return True

    def run_mcp_command(self, cmd_args):
        account = self.get_current_account()
        if not account:
            print("No valid accounts found.")
            return None

        env = os.environ.copy()
        env["NOTEBOOKLM_SESSION_ID"] = account["session_id"]
        env["NOTEBOOKLM_SESSION_PAPISID"] = account["papisid"]

        full_cmd = [str(UV_PATH), "tool", "run", "notebooklm-mcp"] + cmd_args
        
        print(f"Executing command with account: {account['id']}")
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate()
        
        # Check for failure indicators
        output = (stdout or "") + (stderr or "")
        failure_indicators = ["limit reached", "rate limit", "quota exceeded", "access denied"]
        
        if any(indicator in output.lower() for indicator in failure_indicators):
            print(f"Account {account['id']} hit a limit. Rotating...")
            if self.rotate_account():
                return self.run_mcp_command(cmd_args) # Retry with next account
        
        return stdout, stderr, process.returncode

if __name__ == "__main__":
    import sys
    # Force UTF-8 for output
    if sys.platform == "win32":
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        
    manager = NotebookManager()
    if len(sys.argv) > 1:
        stdout, stderr, code = manager.run_mcp_command(sys.argv[1:])
        if stdout:
            sys.stdout.buffer.write(stdout.encode('utf-8', errors='replace'))
            sys.stdout.buffer.flush()
        if stderr:
            sys.stderr.buffer.write(stderr.encode('utf-8', errors='replace'))
            sys.stderr.buffer.flush()
        sys.exit(code)
    else:
        print(f"Loaded {len(manager.accounts)} accounts.")
        for acc in manager.accounts:
            print(f" - {acc['id']}")
