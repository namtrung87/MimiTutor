"""
Playwright-based NotebookLM Automation - FINAL ROBUST VERSION
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
    try:
        browser = await p.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
    except:
        try:
             browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        except Exception as e:
            print(f"  Launch failed: {e}")
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
        
        if "accounts.google.com" in page.url:
            print("  Login required.")
            await browser.close()
            return None
        
        # Create Notebook
        print("  Creating notebook...")
        try:
            # Click upper left 'New notebook'
            await page.click("div.create-new-notebook, button", timeout=5000)
        except:
             # Just try clicking the first 'New' text
             try:
                 await page.click("text=New notebook")
             except:
                 pass
        
        await page.wait_for_url("**/notebook/**", timeout=30000)
        print(f"  Created: {page.url}")
        
        # Chat
        print("  Locating chat...")
        # Generic fallback
        await page.wait_for_selector("textarea", timeout=30000)
        
        briefing = BRIEFING_FILE.read_text(encoding='utf-8')
        prompt = f"Context:\n{briefing}\n\nTask: Create a 7-slide outline for Science Unit 8. List Title, Bullets, and Notes for each."
        
        # Fill generic textarea
        inputs = await page.locator("textarea").all()
        # usually last one is chat
        if inputs:
            await inputs[-1].fill(prompt)
            await inputs[-1].press("Enter")
            print("  Prompt sent. Waiting 45s...")
            await page.wait_for_timeout(45000)
            
            # Save dump
            text = await page.inner_text("body")
            (OUTPUT_DIR / "Unit8_NotebookLM_Slides_Automated_FINAL.md").write_text(text, encoding='utf-8')
            
            # Screenshot
            await page.screenshot(path=str(OUTPUT_DIR / "NotebookLM_Final_Result.png"), full_page=True)
            print("  SAVED!")
            await browser.close()
            return True
            
    except Exception as e:
        print(f"  Error: {e}")
        await browser.close()
        return None

async def main():
    print("Starting FINAL Automation...")
    async with async_playwright() as p:
        # Try accounts in reverse order (to avoid locked/timed out ones)
        cookie_files = sorted(COOKIES_DIR.glob("*.txt"), reverse=True)
        for cookie_file in cookie_files:
            if await try_account(p, cookie_file):
                break

if __name__ == "__main__":
    asyncio.run(main())
