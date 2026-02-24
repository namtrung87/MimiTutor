"""
NotebookLM Automation V3 - The Final Fix
Goal: Create NEW notebook, Capture URL, Generate Slides, Return URL
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
SLIDES_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning\Unit8_Science_Slides_Outline.md")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

# Proven account
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

async def main():
    print("Starting V3 Automation...")
    cookie_file = COOKIES_DIR / TARGET_ACCOUNT
    cookies = parse_netscape_cookies(cookie_file)
    
    async with async_playwright() as p:
        print("  Launching Chrome...")
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
        
        # Click New Notebook
        print("  Creating New Notebook...")
        # Use precise selector for the "New Notebook" tile
        # It's usually a div with class 'notebook-grid-item create' or similar
        # We search specifically for the text "New notebook"
        created = False
        try:
            # Wait for dashboard
            await page.wait_for_selector(".notebook-grid-item", timeout=15000)
            
            # Click
            await page.click("div.notebook-grid-item >> text=New notebook")
            created = True
        except:
            # Fallback
            try:
                await page.click("text=New notebook")
                created = True
            except:
                pass
        
        if not created:
            print("  Failed to click create.")
            await browser.close()
            return

        print("  Waiting for Notebook URL...")
        try:
            await page.wait_for_url("**/notebook/**", timeout=30000)
        except:
             print("  URL timeout.")
             
        # CAPTURE URL
        notebook_url = page.url
        print(f"  Captured URL: {notebook_url}")
        (OUTPUT_DIR / "new_notebook_url.txt").write_text(notebook_url, encoding='utf-8')
        
        if "/notebook/" not in notebook_url:
            print("  Warning: URL does not look like a notebook.")
            
        # Add Sources (Chat Injection)
        print("  Injecting Content...")
        try:
            await page.wait_for_selector("textarea", timeout=30000)
            inputs = await page.locator("textarea").all()
            chat_input = inputs[-1]
            
            # Prepare Prompt
            slides_content = SLIDES_FILE.read_text(encoding='utf-8')
            prompt = f"""I need you to create a slide deck based on this content.
CONTENT:
{slides_content}
---
TASK:
Generate a polished 7-slide outline from the content above.
"""
            await chat_input.fill(prompt)
            await chat_input.press("Enter")
            
            print("  Generating Slides (waiting 45s)...")
            await page.wait_for_timeout(45000)
            
            # Save Output
            content = await page.inner_text("body")
            (OUTPUT_DIR / "Unit8_NotebookLM_Slides_Final_Auto.txt").write_text(content, encoding='utf-8')
            await page.screenshot(path=str(OUTPUT_DIR / "Final_V3_Result.png"), full_page=True)
            print("  SUCCESS!")
            
        except Exception as e:
            print(f"  Error in chat: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
