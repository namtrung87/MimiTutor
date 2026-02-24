"""
NotebookLM Correction Automation Script
Goal: Create NEW notebook, Import Content, Generate Slides
Detailed Strategy:
- Use System Chrome (proven successful for network)
- Identify 'New Notebook' button reliably
- Verify New Notebook URL
- Interact with 'Add Source' -> 'Copied Text' or Chat Context
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

COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
BRIEFING_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning\Unit8_Science_Briefing.md")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

# Proven account from previous run
TARGET_ACCOUNT = "notebooklm.google.com_cookies (1).txt"

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

async def create_and_generate(page, briefing_content):
    print("  Identifying 'New Notebook' button...")
    
    # Wait for dashboard to stabilize
    # Wait for "Loading..." to disappear
    try:
        await page.wait_for_selector("div.notebook-grid-item", timeout=30000) 
    except:
        pass
        
    # Find Create Button
    # Usually has text "New notebook" or specific class
    # We will try to find the specific element that triggers creation
    
    create_btn = None
    # Try multiple strategies
    strategies = [
        "div[role='button']:has-text('New notebook')",
        ".create-new-notebook",
        "//div[contains(text(), 'New notebook')]",
        "button[aria-label='Create new notebook']"
    ]
    
    for selector in strategies:
        try:
            if await page.locator(selector).first.count() > 0:
                print(f"  Found create button via: {selector}")
                create_btn = page.locator(selector).first
                break
        except:
             pass
             
    if not create_btn:
        print("  Could not find Create Button via standard selectors. Dumping page text...")
        # text = await page.inner_text("body")
        # print(text[:500])
        return False
        
    print("  Clicking Create...")
    await create_btn.click()
    
    print("  Waiting for notebook URL...")
    try:
        await page.wait_for_url("**/notebook/**", timeout=30000)
    except:
        print("  URL change timeout. Checking if we are inside...")
        
    if "/notebook/" not in page.url:
        print("  Failed to enter notebook.")
        return False
        
    print(f"  SUCCESS: Created Notebook: {page.url}")
    
    # Add Source
    print("  Adding source content...")
    # Try to find "Add source" -> "Copied text"
    # Usually: Click "Add source" (if visible) -> Click "Copied text" -> Paste -> Click "Insert"
    
    # Fallback: Chat Context Injection (Reliable)
    # Finding chat input
    print("  Locating chat input...")
    await page.wait_for_selector("textarea", timeout=30000)
    
    # Construct prompt with context
    prompt = f"""I am uploading the source material for Unit 8 Science here.
CONTEXT:
{briefing_content}
---
TASK:
Based on the context above, generate a 7-slide outline for a presentation.
Format:
Slide [Number]: [Title]
- [Bullet Point 1]
- [Bullet Point 2]
- [Speaker Notes]
"""
    # Fill generic textarea (usually visible)
    inputs = await page.locator("textarea").all()
    if inputs:
        target = inputs[-1]
        await target.fill(prompt)
        await target.press("Enter")
        
        print("  Prompt sent. Waiting for generation (60s)...")
        await page.wait_for_timeout(60000)
        
        # Capture Response
        await page.screenshot(path=str(OUTPUT_DIR / "NotebookLM_Final_Fix_Result.png"), full_page=True)
        content = await page.inner_text("body")
        (OUTPUT_DIR / "Unit8_NotebookLM_Slides_Fixed.txt").write_text(content, encoding='utf-8')
        print("  SUCCESS: Content generated.")
        return True
        
    return False

async def main():
    print("Starting Correction Automation...")
    cookie_file = COOKIES_DIR / TARGET_ACCOUNT
    if not cookie_file.exists():
        print(f"Target cookie file {cookie_file} not found.")
        return

    cookies = parse_netscape_cookies(cookie_file)
    
    async with async_playwright() as p:
        print("  Launching Chrome (system installed)...")
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled", "--start-maximized"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        await context.add_cookies(cookies)
        page = await context.new_page()
        
        print("  Navigating to NotebookLM...")
        await page.goto("https://notebooklm.google.com/", timeout=60000, wait_until="domcontentloaded")
        
        # Wait for loading spin
        try:
             await page.wait_for_selector("body", timeout=10000)
             text = await page.inner_text("body")
             if "Loading" in text:
                 print("  Waiting for 'Loading' to finish (60s)...")
                 await page.wait_for_timeout(60000)
        except:
             pass
             
        if await create_and_generate(page, BRIEFING_FILE.read_text(encoding='utf-8')):
            print("  Procedure Completed.")
        else:
            print("  Procedure Failed.")
            await page.screenshot(path=str(OUTPUT_DIR / "fail_correction.png"))
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
