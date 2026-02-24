"""
NotebookLM Ultra-Robust Automation Script
Features:
- Playwright Stealth
- Extended Timeouts (300s)
- Aggressive Error Handling & Logging
- Diagnostics Screenshots
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

# Import stealth (if installed)
try:
    from playwright_stealth import stealth_async
except ImportError:
    print("Warning: playwright-stealth not installed. Acting normal.")
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
        # Launch with specific args for stability
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--mute-audio" 
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        # Apply stealth
        if stealth_async:
            await stealth_async(page)
        
        print("  Navigating to NotebookLM (Timeout 60s)...")
        try:
            await page.goto("https://notebooklm.google.com/", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"  Navigation error: {e}")
            # Sometimes network change errors occur but page loads partially
        
        # Check URL
        print(f"  Current URL: {page.url}")
        if "accounts.google.com" in page.url:
            print("  FAIL: Redirected to login page.")
            await page.screenshot(path=str(OUTPUT_DIR / f"fail_login_{cookie_file.stem}.png"))
            await browser.close()
            return None
            
        # Check Title
        title = await page.title()
        print(f"  Page Title: {title}")
        
        # Wait for meaningful content
        # NotebookLM home usually has "Welcome" or "Notebooks"
        print("  Waiting for main content...")
        try:
            # Wait for either 'create new' button OR existing notebooks OR welcome text
            # We use a very generous timeout
            await page.wait_for_selector("body", timeout=30000)
        except:
             print("  Body not found??")
        
        # Save debug screenshot of home
        await page.screenshot(path=str(OUTPUT_DIR / f"debug_home_{cookie_file.stem}.png"))
        
        # Try to Create Notebook
        print("  Attempting to create notebook...")
        created = False
        try:
            # Try click "New notebook" (button or div)
            # Use strict mode off to find any match
            target = page.locator("text=New notebook").first
            if await target.count() > 0:
                print("  Found 'New notebook' text...")
                await target.click(timeout=10000)
                created = True
            else:
                # Try finding via class
                target = page.locator(".create-new-notebook").first
                if await target.count() > 0:
                    print("  Found .create-new-notebook...")
                    await target.click(timeout=10000)
                    created = True
                
        except Exception as e:
            print(f"  Create click failed: {e}")
            
        if not created:
             print("  Could not click create. Dumping page text...")
             text = await page.inner_text("body")
             print(f"  Page Text Start: {text[:200]}")
             # Maybe we are already inside a notebook?
             if "/notebook/" in page.url:
                 print("  Already inside a notebook!")
                 created = True
             else:
                 await browser.close()
                 return None
        
        # Wait for notebook load
        print("  Waiting for notebook URL (Timeout 60s)...")
        try:
            await page.wait_for_url("**/notebook/**", timeout=60000)
        except:
            print("  URL did not change to /notebook/...")
            # Check if we see chat input anyway
            
        # Check for Chat Input
        print("  Looking for chat input...")
        chat_found = False
        chat_input = None
        
        try:
            # Try multiple selectors
            selectors = ["textarea", "input[type='text']", "[contenteditable]"]
            for sel in selectors:
                count = await page.locator(sel).count()
                print(f"  Found {count} elements for '{sel}'")
                if count > 0:
                    # Usually the last one is the main chat
                    chat_input = page.locator(sel).last
                    if await chat_input.is_visible():
                         print(f"  Using selector: {sel}")
                         chat_found = True
                         break
        except Exception as e:
            print(f"  Chat search error: {e}")
            
        if not chat_found:
            print("  FAIL: No chat input found.")
            await page.screenshot(path=str(OUTPUT_DIR / f"fail_nochat_{cookie_file.stem}.png"))
            await browser.close()
            return None
            
        # Send Prompt
        print("  Sending prompt...")
        briefing = BRIEFING_FILE.read_text(encoding='utf-8')
        prompt = f"INSTRUCTION: Create a 7-slide outline for Unit 8 Science based on this:\n\n{briefing[:2000]}..." # Truncate to be safe
        
        await chat_input.fill(prompt)
        await chat_input.press("Enter")
        
        print("  Prompt sent! Waiting for response (Timeout 120s)...")
        # Wait for response bubble to appear
        # We look for a new element appearing in the chat list
        # Or just wait blindly
        await page.wait_for_timeout(45000)
        
        # Save Result
        print("  Capturing result...")
        await page.screenshot(path=str(OUTPUT_DIR / "NotebookLM_Robust_Result.png"), full_page=True)
        
        # Dump text
        content = await page.inner_text("body")
        (OUTPUT_DIR / "Unit8_NotebookLM_Slides_Robust.txt").write_text(content, encoding='utf-8')
        print("  SUCCESS: Content saved.")
        
        await browser.close()
        return True

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
    print("Starting Robust Automation...")
    async with async_playwright() as p:
        # Try Account 2 first (it seemed most promising before)
        # Or try all
        files = sorted(COOKIES_DIR.glob("*.txt"))
        # Prioritize (2) and (5) based on previous logs?
        # Let's just try them all, but start with the one that got furthest (2)
        # Reorder to put (2) first if exists
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
