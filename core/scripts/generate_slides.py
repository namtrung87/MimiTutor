"""
Automated NotebookLM Slide Generator for Unit 8 Science
Uses notebooklm-mcp tool with local cookie authentication
"""
import os
import sys
import subprocess
import json
import time
from pathlib import Path

# Force UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# Configuration
UV_PATH = Path(r"C:\Users\Trung Nguyen\.local\bin\uv.exe")
COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
BRIEFING_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning\Unit8_Science_Briefing.md")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

def get_cookie_env(cookie_file):
    """Parse cookie file and return env vars for notebooklm-mcp"""
    env = os.environ.copy()
    session_id = None
    papisid = None
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                if "__Secure-1PSID" in line and "__Secure-1PSIDTS" not in line and "__Secure-1PSIDCC" not in line:
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        session_id = parts[6].strip()
                if "__Secure-1PAPISID" in line:
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        papisid = parts[6].strip() or parts[5].strip()
    except Exception as e:
        print(f"Error parsing {cookie_file}: {e}")
        return None
    
    if session_id and papisid:
        env["NOTEBOOKLM_SESSION_ID"] = session_id
        env["NOTEBOOKLM_SESSION_PAPISID"] = papisid
        return env
    return None

def run_mcp(args, env, timeout=120):
    """Run notebooklm-mcp with given args and env"""
    cmd = [str(UV_PATH), "tool", "run", "notebooklm-mcp"] + args
    print(f"  Running: {' '.join(args)}")
    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=timeout
        )
        output = (result.stdout or "") + (result.stderr or "")
        print(f"  Exit code: {result.returncode}")
        if output.strip():
            print(f"  Output: {output[:500]}")
        return result.returncode, output
    except subprocess.TimeoutExpired:
        print(f"  Timeout after {timeout}s")
        return -1, "timeout"
    except Exception as e:
        print(f"  Error: {e}")
        return -1, str(e)

def try_account(cookie_file):
    """Try a single account to create notebook and generate slides"""
    print(f"\n{'='*60}")
    print(f"Trying account: {cookie_file.name}")
    print(f"{'='*60}")
    
    env = get_cookie_env(cookie_file)
    if not env:
        print("  Failed to parse cookies, skipping...")
        return False

    # Step 1: Test connection
    print("\n[Step 1] Testing connection...")
    code, output = run_mcp(["test"], env, timeout=60)
    if code != 0:
        print("  Connection test failed, skipping this account...")
        return False
    
    print("  Connection OK!")
    
    # Step 2: Use chat to create content and generate slides
    # Read the briefing content
    briefing_content = BRIEFING_FILE.read_text(encoding='utf-8')
    
    # Create a detailed prompt for slide generation
    slide_prompt = f"""Please create a detailed presentation slide deck about "Unit 8: Changes to Materials" for Cambridge Lower Secondary Science 7. 
    
Here is the source content:

{briefing_content}

Please create slides with the following structure:
- Slide 1: Title slide
- Slide 2: Physical vs Chemical Changes (with examples)
- Slide 3: 5 Signs of a Chemical Reaction
- Slide 4: Reactants and Products (with word equations)
- Slide 5: The pH Scale (0-14 rainbow)
- Slide 6: Acids, Alkalis, and Neutralization
- Slide 7: Gas Testing Methods

For each slide, provide:
1. A clear title
2. Key bullet points with simple explanations
3. Visual description suggestions
4. A fun fact or memorable tip for a young student

Make it engaging and easy to understand for a 12-year-old girl."""

    print("\n[Step 2] Sending chat message to generate slides...")
    code, output = run_mcp(
        ["chat", "--headless", "-m", slide_prompt],
        env, timeout=120
    )
    
    if code == 0 and output.strip():
        # Save the output
        output_file = OUTPUT_DIR / "Unit8_NotebookLM_Slides.md"
        output_file.write_text(output, encoding='utf-8')
        print(f"\n  SUCCESS! Slides saved to: {output_file}")
        return True
    else:
        print(f"  Chat command returned code {code}")
        return False

def main():
    print("=" * 60)
    print("NotebookLM Automated Slide Generator")
    print("Unit 8: Changes to Materials - Science 7")
    print("=" * 60)
    
    # Find all cookie files
    cookie_files = sorted(COOKIES_DIR.glob("*.txt"))
    print(f"\nFound {len(cookie_files)} account(s)")
    
    if not cookie_files:
        print("ERROR: No cookie files found!")
        sys.exit(1)
    
    # Try each account until one works
    for cookie_file in cookie_files:
        success = try_account(cookie_file)
        if success:
            print(f"\n{'='*60}")
            print("DONE! Slides generated successfully.")
            print(f"{'='*60}")
            return
    
    print(f"\n{'='*60}")
    print("WARNING: All accounts failed or timed out.")
    print("The slide content has been prepared locally.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
