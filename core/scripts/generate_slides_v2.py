"""
NotebookLM Browser Automation - Create Notebook & Generate Slides
Uses undetected-chromedriver with cookie injection
"""
import sys
import os
import time
import json
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
BRIEFING_FILE = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning\Unit8_Science_Briefing.md")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

def parse_netscape_cookies(cookie_file):
    """Parse Netscape format cookie file into Selenium cookie dicts"""
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
                        "domain": parts[0],
                        "httpOnly": parts[1].upper() == "TRUE",
                        "path": parts[2],
                        "secure": parts[3].upper() == "TRUE",
                        "name": parts[5],
                        "value": parts[6],
                    }
                    # Only add google.com cookies
                    if "google.com" in cookie["domain"]:
                        cookies.append(cookie)
    except Exception as e:
        print(f"  Error parsing {cookie_file}: {e}")
    return cookies

def try_account(cookie_file):
    """Try a single account: inject cookies, create notebook, generate slides"""
    print(f"\n{'='*60}")
    print(f"Account: {cookie_file.name}")
    print(f"{'='*60}")
    
    cookies = parse_netscape_cookies(cookie_file)
    if not cookies:
        print("  No valid cookies found, skipping...")
        return None
    
    print(f"  Parsed {len(cookies)} cookies")
    
    driver = None
    try:
        # Launch Chrome
        print("  Launching Chrome (headless)...")
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=en-US")
        
        driver = uc.Chrome(options=options, use_subprocess=True)
        wait = WebDriverWait(driver, 30)
        
        # Step 1: Navigate to google.com to set cookie domain
        print("  [1/5] Setting up cookies on google.com...")
        driver.get("https://www.google.com")
        time.sleep(2)
        
        # Inject cookies
        for cookie in cookies:
            try:
                # Clean domain for selenium
                clean_cookie = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                    "secure": cookie["secure"],
                }
                driver.add_cookie(clean_cookie)
            except Exception:
                pass  # Some cookies may fail domain check
        
        print(f"  Cookies injected")
        
        # Step 2: Navigate to NotebookLM
        print("  [2/5] Navigating to NotebookLM...")
        driver.get("https://notebooklm.google.com/")
        time.sleep(5)
        
        # Check if we're logged in
        page_source = driver.page_source
        current_url = driver.current_url
        print(f"  Current URL: {current_url}")
        
        if "accounts.google.com" in current_url:
            print("  Not logged in - cookies may be expired")
            return None
        
        # Step 3: Create a new notebook
        print("  [3/5] Creating new notebook...")
        time.sleep(3)
        
        # Look for "New notebook" or "Create" button
        try:
            # Try different selectors for the create button
            create_selectors = [
                "//button[contains(., 'New')]",
                "//button[contains(., 'Create')]",
                "//a[contains(., 'New notebook')]",
                "//button[contains(@aria-label, 'Create')]",
                "//div[contains(@class, 'create')]",
                "//button[contains(@class, 'new')]",
            ]
            
            create_btn = None
            for selector in create_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        create_btn = elements[0]
                        print(f"  Found create button with: {selector}")
                        break
                except:
                    continue
            
            if create_btn:
                create_btn.click()
                time.sleep(5)
                print(f"  New notebook created! URL: {driver.current_url}")
            else:
                # Maybe we're already in a notebook creation flow
                print(f"  No create button found. Page title: {driver.title}")
                # Save screenshot for debugging
                screenshot_path = str(OUTPUT_DIR / "notebooklm_debug.png")
                driver.save_screenshot(screenshot_path)
                print(f"  Screenshot saved: {screenshot_path}")
                
                # Print page source snippet for debugging
                print(f"  Page source preview: {page_source[:500]}")
        except Exception as e:
            print(f"  Error creating notebook: {e}")
        
        # Step 4: Add source content
        print("  [4/5] Adding source content...")
        notebook_url = driver.current_url
        
        # Read briefing content
        briefing_content = BRIEFING_FILE.read_text(encoding='utf-8')
        
        # Try to find a text input / paste area
        try:
            # Look for "Add source" or paste text option
            source_selectors = [
                "//button[contains(., 'source')]",
                "//button[contains(., 'Add')]",
                "//button[contains(., 'Paste')]",
                "//button[contains(., 'text')]",
                "//textarea",
                "//div[@contenteditable='true']",
            ]
            
            for selector in source_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        print(f"  Found input with: {selector}")
                        elements[0].click()
                        time.sleep(2)
                        break
                except:
                    continue
            
            # Try to paste text
            text_areas = driver.find_elements(By.XPATH, "//textarea | //div[@contenteditable='true']")
            if text_areas:
                text_areas[0].send_keys(briefing_content)
                time.sleep(2)
                print("  Content pasted!")
            
        except Exception as e:
            print(f"  Error adding source: {e}")
        
        # Step 5: Request slides via chat
        print("  [5/5] Requesting slide generation...")
        time.sleep(3)
        
        try:
            # Find the chat input
            chat_selectors = [
                "//textarea[contains(@placeholder, '')]",
                "//div[@contenteditable='true']",
                "//input[@type='text']",
            ]
            
            chat_input = None
            for selector in chat_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        chat_input = elements[-1]  # Usually the last one is the chat
                        print(f"  Found chat input with: {selector}")
                        break
                except:
                    continue
            
            if chat_input:
                slide_prompt = (
                    "Create a detailed presentation/slide deck about Unit 8: Changes to Materials. "
                    "Include slides about: 1) Physical vs Chemical Changes, "
                    "2) 5 Signs of Chemical Reactions, "
                    "3) Reactants and Products with word equations, "
                    "4) pH Scale, "
                    "5) Neutralization, "
                    "6) Gas Testing Methods. "
                    "Make it engaging for a 12-year-old student."
                )
                
                chat_input.clear()
                chat_input.send_keys(slide_prompt)
                time.sleep(1)
                chat_input.send_keys(Keys.RETURN)
                
                print("  Prompt sent! Waiting for response...")
                time.sleep(15)
                
                # Capture the response
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Save everything
                output_file = OUTPUT_DIR / "Unit8_NotebookLM_Slides.md"
                output_file.write_text(page_text, encoding='utf-8')
                print(f"  Response saved to: {output_file}")
                
                # Save screenshot
                screenshot_path = str(OUTPUT_DIR / "notebooklm_result.png")
                driver.save_screenshot(screenshot_path)
                print(f"  Screenshot saved: {screenshot_path}")
                
                return notebook_url
            else:
                print("  No chat input found")
                screenshot_path = str(OUTPUT_DIR / "notebooklm_nochat.png")
                driver.save_screenshot(screenshot_path)
                print(f"  Debug screenshot: {screenshot_path}")
                
        except Exception as e:
            print(f"  Error in chat: {e}")
        
        return notebook_url
        
    except Exception as e:
        print(f"  Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    print("=" * 60)
    print("NotebookLM Automated Slide Generator v2")
    print("Unit 8: Changes to Materials - Science 7")
    print("=" * 60)
    
    cookie_files = sorted(COOKIES_DIR.glob("*.txt"))
    print(f"\nFound {len(cookie_files)} account(s)")
    
    for cookie_file in cookie_files:
        result = try_account(cookie_file)
        if result:
            print(f"\n{'='*60}")
            print(f"SUCCESS! Notebook URL: {result}")
            print(f"Check output in: {OUTPUT_DIR}")
            print(f"{'='*60}")
            return
    
    print(f"\n{'='*60}")
    print("All accounts failed. Check cookie freshness.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
