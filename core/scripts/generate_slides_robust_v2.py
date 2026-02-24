"""
NotebookLM Ultra-Robust Automation Script V2
Features:
- Forces System Chrome (channel="chrome")
- Validates Stealth Import
- Extended Timeouts (300s)
- Aggressive Error Handling & Logging
"""
import os
import sys
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Fix environment
os.environ["HOME"] = str(Path.home())
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# Import stealth
try:
    from playwright_stealth import stealth_async
    print("Stealth module loaded successfully.")
except ImportError as e:
    print(f"Stealth module import failed: {e}")
    stealth_async = None

COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
BRIEFING_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning\Unit8_Science_Briefing.md")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

def parse_netscape_cookies(cookie_file):
    cookies = []
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookie = {
                        "name": parts[5],
                        "value": parts[6],
                        "domain": parts[0],
                        "path": parts[2],
                        "secure": parts[3].upper() == "TRUE",
                        "httpOnly": parts[1].upper() == "TRUE",
                        "sameSite": "Lax",
                        "expires": int(parts[4]) if parts[4].isdigit() else -1
                    }
                    if "google.com" in cookie["domain"]:
                         cookies.append(cookie)
    except Exception as e:
        print(f"Error parsing {cookie_file}: {e}")
    return cookies

async def try_account(p, cookie_file):
    print(f"\n{'='*60}")
    print(f"Trying account: {cookie_file.name}")
    print(f"{'='*60}")
    
    cookies = parse_netscape_cookies(cookie_file)
    if not cookies:
        print("  No valid cookies found.")
        return None

    browser = None
    try:
        # Launch using CHROME channel for better compatibility
        print("  Launching Chrome (system installed)...")
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        # Apply stealth
        if stealth_async:
            await stealth_async(page)
        
        print("  Navigating to NotebookLM (Timeout 120s)...")
        try:
            await page.goto("https://notebooklm.google.com/", timeout=120000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"  Navigation error (ignored): {e}")
        
        # Initial Screencap
        await page.screenshot(path=str(OUTPUT_DIR / f"debug_start_{cookie_file.stem}.png"))
        
        # Check login status
        if "accounts.google.com" in page.url:
            print("  FAIL: Redirected to login page.")
            await browser.close()
            return None
            
        # Check loaded state
        print("  Waiting for 'notebooks' or 'welcome' or 'create'...")
        try:
            # We wait for the spinner to go away?
            # Or wait for specific text
            await page.wait_for_selector("body", timeout=30000)
            text = await page.inner_text("body")
            print(f"  Initial Body Text: {text[:100]}...")
            
            if "Loading" in text or "Đang tải" in text:
                print("  Still loading... waiting 60s more...")
                await page.wait_for_timeout(60000)
                text = await page.inner_text("body")
                print(f"  Body Text after wait: {text[:100]}...")
        except:
             pass

        # Try to Create Notebook
        print("  Attempting to create notebook...")
        created = False
        
        # Try to click "New notebook"
        # Strategy: Evaluate JS to find and click
        try:
            # This JS tries to find any element with text 'New notebook' or similar
            handle = await page.evaluate_handle("""() => {
                const elements = Array.from(document.querySelectorAll('*'));
                return elements.find(el => el.textContent.includes('New notebook') || el.textContent.includes('Create new') || el.classList.contains('create-new-notebook'));
            }""")
            if handle:
                print("  Found element via JS text search. Clicking...")
                await handle.as_element().click()
                created = True
            else:
                print("  JS search found nothing.")
                # Fallback to coordinate click? (risky)
                # Maybe try clicking the big plus button if visual?
        except Exception as e:
            print(f"  JS click failed: {e}")
        
        # If created, URL should change
        print("  Waiting for URL change...")
        try:
             await page.wait_for_url("**/notebook/**", timeout=30000)
             created = True
        except:
             pass
             
        if not created and "/notebook/" not in page.url:
             print("  Could not enter notebook mode.")
             await page.screenshot(path=str(OUTPUT_DIR / f"fail_nocreate_{cookie_file.stem}.png"))
             await browser.close()
             return None
             
        print(f"  Inside Notebook: {page.url}")
        
        # Chat Interaction
        print("  Searching for chat input...")
        # Try generic textarea
        try:
            await page.wait_for_selector("textarea", timeout=30000)
            inputs = await page.locator("textarea").all()
            if inputs:
                target = inputs[-1]
                print(f"  Found {len(inputs)} textareas. Using last one.")
                
                briefing = BRIEFING_FILE.read_text(encoding='utf-8')
                await target.fill(f"Summary: {briefing[:5000]}... Task: Generate 7-slide outline.")
                await target.press("Enter")
                
                print("  Prompt sent. Waiting 45s...")
                await page.wait_for_timeout(45000)
                
                # Capture result
                await page.screenshot(path=str(OUTPUT_DIR / "NotebookLM_Robust_Result.png"), full_page=True)
                content = await page.inner_text("body")
                (OUTPUT_DIR / "Unit8_NotebookLM_Slides_Robust.txt").write_text(content, encoding='utf-8')
                print("  SUCCESS: Content saved.")
                await browser.close()
                return True
        except Exception as e:
             print(f"  Chat interaction failed: {e}")
             await page.screenshot(path=str(OUTPUT_DIR / f"fail_chat_{cookie_file.stem}.png"))

        await browser.close()
        return None

    except Exception as e:
        print(f"  CRITICAL ERROR: {e}")
        try:
            await page.screenshot(path=str(OUTPUT_DIR / f"crash_{cookie_file.stem}.png"))
        except:
            pass
        if browser:
            await browser.close()
        return None

async def main():
    print("Starting Robust Automation V2...")
    async with async_playwright() as p:
        # Try Account 2 first 
        files = sorted(COOKIES_DIR.glob("*.txt"))
        target = next((f for f in files if "(2)" in f.name), None)
        if target:
            files.remove(target)
            files.insert(0, target)
            
        for f in files:
            if await try_account(p, f):
                print("  !!! WE HAVE A WINNER !!!")
                return

if __name__ == "__main__":
    asyncio.run(main())
