"""
Playwright-based NotebookLM Automation - Robust Version
"""
import os
import sys
import time
import json
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright

# Fix environment
os.environ["HOME"] = str(Path.home())
# Force UTF8
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

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
    print(f"\nTrying account: {cookie_file.name}")
    cookies = parse_netscape_cookies(cookie_file)
    if not cookies:
        return None

    browser = None
    # Try multiple channels
    channels = ["chromium", "chrome", "msedge"]
    
    for channel in channels:
        print(f"  Attempting launch with channel: {channel}")
        try:
            if channel == "chromium":
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            else:
                browser = await p.chromium.launch(channel=channel, headless=True, args=["--no-sandbox"])
            break
        except Exception as e:
            print(f"  Failed to launch {channel}: {e}")
            
    if not browser:
        print("  Could not launch any browser.")
        return None

    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        print("  Navigating to NotebookLM...")
        await page.goto("https://notebooklm.google.com/", timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        # Check login
        if "accounts.google.com" in page.url:
            print("  Redirected to login - cookies expired or invalid")
            await browser.close()
            return None
        
        # Check for 'New Notebook'
        print("  Checking for creating notebook...")
        try:
            # Try specific selectors
            await page.wait_for_selector("div.create-new-notebook, button[aria-label='Create new notebook'], .notebook-grid-item.create", timeout=10000)
            
            # Click it
            # We try a few clicks
            clicked = False
            for selector in ["div.create-new-notebook", "button[aria-label='Create new notebook']", ".notebook-grid-item.create"]:
                if await page.locator(selector).count() > 0:
                    await page.click(selector)
                    clicked = True
                    break
            
            if not clicked:
                 await page.click("text=New notebook")
                 
        except Exception as e:
            print(f"  Could not find create button: {e}")
            # Maybe already created? Capture screenshot
            await page.screenshot(path=str(OUTPUT_DIR / f"debug_nocreate_{cookie_file.stem}.png"))
            await browser.close()
            return None
            
        # Wait for notebook
        print("  Waiting for notebook...")
        await page.wait_for_url("**/notebook/**", timeout=30000)
        notebook_url = page.url
        print(f"  Created notebook: {notebook_url}")
        
        # Add Source / Chat
        print("  Adding source via chat...")
        
        # Try to find chat input
        # Specific selector for NotebookLM chat
        chat_selector = "textarea[placeholder*='instructions'], textarea[placeholder*='questions']"
        await page.wait_for_selector(chat_selector, timeout=20000)
        
        briefing_content = BRIEFING_FILE.read_text(encoding='utf-8')
        instruction = f"Here is the content for Unit 8 Science:\n\n{briefing_content}\n\nBased on this, generate a Slide Deck Outline with 7 slides, titles, and points."
        
        await page.fill(chat_selector, instruction)
        await page.press(chat_selector, "Enter")
        
        print("  Prompt sent. Waiting for generation (45s)...")
        await page.wait_for_timeout(45000)
        
        # Capture Response
        screenshot_path = OUTPUT_DIR / "NotebookLM_Slides_Final.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  Screenshot saved: {screenshot_path}")
        
        # Get text
        # Try to find the last message
        messages = page.locator("div.model-response-text") 
        count = await messages.count()
        if count > 0:
            text = await messages.last.inner_text()
            text_path = OUTPUT_DIR / "Unit8_NotebookLM_Slides_Automated.md"
            text_path.write_text(text, encoding='utf-8')
            print(f"  Text saved: {text_path}")
        else:
            # Fallback
            full_text = await page.inner_text("body")
            (OUTPUT_DIR / "full_page_dump.txt").write_text(full_text, encoding='utf-8')
            
        await browser.close()
        return notebook_url

    except Exception as e:
        print(f"  Error during automation: {e}")
        try:
             await page.screenshot(path=str(OUTPUT_DIR / f"error_{cookie_file.stem}.png"))
        except:
            pass
        await browser.close()
        return None

async def main():
    print("Starting Robust Playwright Automation...")
    async with async_playwright() as p:
        cookie_files = sorted(COOKIES_DIR.glob("*.txt"))
        for cookie_file in cookie_files:
            result = await try_account(p, cookie_file)
            if result:
                print("SUCCESS!")
                return
    print("All accounts failed.")

if __name__ == "__main__":
    asyncio.run(main())
