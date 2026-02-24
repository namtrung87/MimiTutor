"""
Playwright-based NotebookLM Automation
"""
import os
import sys
import time
import json
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright

# Fix environment for headless browsers (often fails without HOME)
os.environ["HOME"] = str(Path.home())

COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
BRIEFING_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning\Unit8_Science_Briefing.md")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

def parse_netscape_cookies(cookie_file):
    """Parse Netscape cookies for Playwright"""
    cookies = []
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    # Playwright cookie format
                    cookie = {
                        "name": parts[5],
                        "value": parts[6],
                        "domain": parts[0],
                        "path": parts[2],
                        "secure": parts[3].upper() == "TRUE",
                        "httpOnly": parts[1].upper() == "TRUE",
                        "sameSite": "Lax",  # Default often works
                        "expires": int(parts[4]) if parts[4].isdigit() else -1
                    }
                    if "google.com" in cookie["domain"]:
                         cookies.append(cookie)
    except Exception as e:
        print(f"Error parsing {cookie_file}: {e}")
    return cookies

async def try_account(cookie_file):
    print(f"\nTrying account: {cookie_file.name}")
    cookies = parse_netscape_cookies(cookie_file)
    if not cookies:
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        try:
            print("  Navigating to NotebookLM...")
            await page.goto("https://notebooklm.google.com/", timeout=60000)
            await page.wait_for_load_state("networkidle")
            
            # Check login
            if "accounts.google.com" in page.url:
                print("  Redirected to login - cookies expired or invalid")
                await context.close()
                await browser.close()
                return None
            
            # Click New Notebook
            print("  Looking for 'New Notebook' button...")
            new_btn = page.get_by_role("button", name="New notebook")
            if await new_btn.is_visible():
                await new_btn.click()
            else:
                 # Try finding via class or text if role fails
                 new_btn = page.locator("div.create-new-notebook") 
                 if await new_btn.is_visible():
                     await new_btn.click()
                 else:
                     # Maybe just 'New'
                     await page.click("text=New notebook")
            
            # Wait for notebook to load
            print("  Waiting for notebook creation...")
            await page.wait_for_url("**/notebook/**", timeout=30000)
            notebook_url = page.url
            print(f"  Created notebook: {notebook_url}")
            
            # Add Source
            print("  Adding source content...")
            # NotebookLM usually has a "Add source" or "Link text" area
            # We'll try to find the "Paste text" option or just paste into the chat if sources are tricky
            
            # Actually, let's look for "Add source" -> "Copied text"
            # But the UI might have changed. 
            # Strategy: Just use the chat to "teach" it.
            
            # Find chat input
            print("  Locating chat input...")
            # The chat input usually has a placeholder like "Ask questions..."
            chat_input = page.get_by_placeholder("Enter instructions or questions")
            if not await chat_input.is_visible():
                chat_input = page.locator("textarea")
            
            if await chat_input.is_visible():
                briefing_content = BRIEFING_FILE.read_text(encoding='utf-8')
                
                # First, seed the knowledge
                instruction = f"Here is the content for our lesson on Science Unit 8. Please analyze it:\n\n{briefing_content}"
                await chat_input.fill(instruction[:15000]) # Truncate if too long, but text is short
                await chat_input.press("Enter")
                
                print("  Uploaded content via chat. Waiting for processing...")
                await page.wait_for_timeout(10000)
                
                # Now ask for slides
                print("  Requesting slides...")
                prompt = (
                    "Based on the text I just gave you, generate a clear Slide Deck Outline for 'Unit 8: Changes to Materials'. "
                    "Include 7 slides with Titles, Bullet Points, and Speaker Notes for a 12-year-old student."
                )
                await chat_input.fill(prompt)
                await chat_input.press("Enter")
                
                # Wait for response generation
                print("  Waiting for response (30s)...")
                await page.wait_for_timeout(30000)
                
                # Capture result
                # Locate the last message bubble
                # This is tricky in DOM, so we'll just grab all text
                content = await page.content()
                
                # Better: take a screenshot of the result
                screenshot_path = OUTPUT_DIR / "NotebookLM_Slides_Result.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"  Screenshot saved to {screenshot_path}")
                
                # Try to extract text
                # We'll dump the whole body text
                body_text = await page.inner_text("body")
                text_path = OUTPUT_DIR / "NotebookLM_Slides_Result.txt"
                text_path.write_text(body_text, encoding='utf-8')
                print(f"  Text debug saved to {text_path}")
                
                return notebook_url
            
        except Exception as e:
            print(f"  Error: {e}")
            await page.screenshot(path=str(OUTPUT_DIR / f"error_{cookie_file.stem}.png"))
        
        await context.close()
        await browser.close()
    return None

async def main():
    print("Starting Playwright Automation...")
    cookie_files = sorted(COOKIES_DIR.glob("*.txt"))
    
    for cookie_file in cookie_files:
        result = await try_account(cookie_file)
        if result:
            print(f"SUCCESS! Notebook: {result}")
            return
    print("All accounts failed.")

if __name__ == "__main__":
    asyncio.run(main())
