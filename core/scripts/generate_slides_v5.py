"""
NotebookLM V5 Complete - Try All Accounts
1. Try each cookie account
2. Create NEW notebook  
3. Upload source files (MD + PDF)
4. Click 'Slide Deck' in Studio
5. Save URL + result
"""
import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

os.environ["HOME"] = str(Path.home())
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

COOKIES_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\NotebookLM")
OUTPUT_DIR = Path(r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Mimi learning")

# Files to import
SOURCE_FILES = [
    OUTPUT_DIR / "Unit8_Science_Briefing.md",
    OUTPUT_DIR / "Unit8_Science_Slides_Outline.md",
    OUTPUT_DIR / "Unit8_NotebookLM_Slides_Final.md",
    OUTPUT_DIR / "pdfcoffee.com_mary-jones-cambridge-lower-secondary-science-7-learnerx27s-book-second-edition-pdf-free.pdf",
]

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
    account_name = cookie_file.stem
    print(f"\n{'='*60}")
    print(f"Trying: {cookie_file.name}")
    print(f"{'='*60}")
    
    cookies = parse_netscape_cookies(cookie_file)
    if not cookies:
        print("  No cookies.")
        return None

    browser = await p.chromium.launch(
        channel="chrome", headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    await context.add_cookies(cookies)
    page = await context.new_page()
    
    try:
        # === PHASE 1: Navigate & Check Login ===
        print("  Navigating to NotebookLM...")
        await page.goto("https://notebooklm.google.com/", timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        if "accounts.google.com" in page.url:
            print("  SKIP: Redirected to login.")
            await browser.close()
            return None
        
        print(f"  Logged in! URL: {page.url}")
        
        # Wait for dashboard to load
        print("  Waiting for dashboard (60s)...")
        for i in range(12):
            text = await page.inner_text("body")
            if "Loading" not in text and "Đang tải" not in text:
                break
            await page.wait_for_timeout(5000)
        
        # === PHASE 2: Create NEW Notebook ===
        print("  Creating new notebook...")
        created = False
        
        # Try clicking "New notebook"
        try:
            await page.click("text=New notebook", timeout=10000)
            created = True
        except:
            try:
                await page.click("text=Create new", timeout=5000)
                created = True
            except:
                pass
        
        if not created:
            print("  Could not click New notebook.")
            text = await page.inner_text("body")
            print(f"  Page: {text[:200]}")
            await browser.close()
            return None
        
        # Wait for notebook URL to become UUID
        print("  Waiting for notebook UUID...")
        notebook_url = ""
        for i in range(30):
            url = page.url
            if "/notebook/" in url and "creating" not in url and "-" in url:
                notebook_url = url
                break
            await page.wait_for_timeout(1000)
        
        if not notebook_url:
            print(f"  URL not stabilized: {page.url}")
            notebook_url = page.url
        
        print(f"  Notebook URL: {notebook_url}")
        (OUTPUT_DIR / "v5_notebook_url.txt").write_text(notebook_url, encoding='utf-8')
        
        # === PHASE 3: Upload Sources ===
        print("\n  --- UPLOADING SOURCES ---")
        await page.wait_for_timeout(5000)
        await page.screenshot(path=str(OUTPUT_DIR / "v5_before_upload.png"))
        
        # Click "Add sources"
        add_clicked = False
        for sel in ["text=Add sources", "text=Add source"]:
            try:
                await page.click(sel, timeout=5000)
                add_clicked = True
                print(f"  Clicked '{sel}'")
                break
            except:
                pass
        
        if not add_clicked:
            # Maybe the "add" icon button
            try:
                # The add button near "Sources" section
                add_icons = page.locator("[aria-label='Add sources']")
                if await add_icons.count() > 0:
                    await add_icons.first.click()
                    add_clicked = True
                    print("  Clicked add icon")
            except:
                pass
        
        if not add_clicked:
            print("  WARNING: Could not click Add sources. Trying file input anyway...")
        
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(OUTPUT_DIR / "v5_add_sources_modal.png"))
        
        # Check for file input
        file_inputs = page.locator("input[type='file']")
        file_count = await file_inputs.count()
        print(f"  Found {file_count} file input(s)")
        
        if file_count > 0:
            # Upload files
            existing = [str(f) for f in SOURCE_FILES if f.exists()]
            print(f"  Uploading {len(existing)} files:")
            for f in existing:
                sz = Path(f).stat().st_size
                print(f"    - {Path(f).name} ({sz/1024:.0f} KB)")
            
            await file_inputs.first.set_input_files(existing)
            print("  Files set! Waiting for upload+processing (180s)...")
            
            # Monitor upload progress
            for i in range(36):  # 36 * 5s = 180s
                await page.wait_for_timeout(5000)
                text = await page.inner_text("body")
                # Check if sources appear in the sidebar
                if "source" in text.lower() and ("1" in text or "2" in text or "3" in text or "4" in text):
                    print(f"  Sources detected after {(i+1)*5}s")
                    break
                if i % 6 == 0:
                    print(f"  Still processing... ({(i+1)*5}s)")
            
            await page.screenshot(path=str(OUTPUT_DIR / "v5_after_upload.png"))
        else:
            # Fallback: paste text via "Copied text"
            print("  No file input. Trying 'Copied text' fallback...")
            try:
                await page.click("text=Copied text", timeout=5000)
                await page.wait_for_timeout(2000)
                
                # Find textarea and paste content
                ta = page.locator("textarea").last
                if await ta.count() > 0:
                    # Combine all MD content
                    combined = ""
                    for f in SOURCE_FILES:
                        if f.exists() and f.suffix == '.md':
                            combined += f"\n\n=== {f.name} ===\n\n"
                            combined += f.read_text(encoding='utf-8')
                    
                    await ta.fill(combined[:50000])  # NotebookLM limit
                    
                    # Click Insert/Add
                    for btn_text in ["Insert", "Add", "Submit"]:
                        try:
                            await page.click(f"button:has-text('{btn_text}')", timeout=3000)
                            print(f"  Clicked '{btn_text}'")
                            break
                        except:
                            pass
                    
                    await page.wait_for_timeout(30000)
                    print("  Pasted text content.")
            except Exception as e:
                print(f"  Paste fallback failed: {e}")
        
        # === PHASE 4: Generate Slide Deck ===
        print("\n  --- GENERATING SLIDE DECK ---")
        await page.wait_for_timeout(5000)
        
        # Click "Slide Deck" in Studio panel
        slide_clicked = False
        for sel in ["text=Slide Deck", "[aria-label='Slide Deck']"]:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.click()
                    slide_clicked = True
                    print(f"  Clicked '{sel}'!")
                    break
            except:
                pass
        
        if not slide_clicked:
            # Try finding via JS
            try:
                await page.evaluate("""() => {
                    const els = Array.from(document.querySelectorAll('*'));
                    const target = els.find(el => el.textContent.trim() === 'Slide Deck');
                    if (target) target.click();
                }""")
                slide_clicked = True
                print("  Clicked 'Slide Deck' via JS!")
            except:
                pass
        
        if slide_clicked:
            print("  Waiting for Slide Deck generation (90s)...")
            await page.wait_for_timeout(90000)
            
            await page.screenshot(path=str(OUTPUT_DIR / "v5_slide_result.png"), full_page=True)
            content = await page.inner_text("body")
            (OUTPUT_DIR / "v5_slide_content.txt").write_text(content, encoding='utf-8')
            
            final_url = page.url
            print(f"  Final URL: {final_url}")
            (OUTPUT_DIR / "v5_final_url.txt").write_text(final_url, encoding='utf-8')
            
            print("\n  SUCCESS!")
        else:
            print("  Could not click Slide Deck.")
            await page.screenshot(path=str(OUTPUT_DIR / "v5_no_slide_btn.png"))
        
        await browser.close()
        return notebook_url
        
    except Exception as e:
        print(f"  CRITICAL ERROR: {e}")
        try:
            await page.screenshot(path=str(OUTPUT_DIR / f"v5_crash_{account_name}.png"))
        except:
            pass
        await browser.close()
        return None

async def main():
    print("=" * 60)
    print("NotebookLM V5 - Complete Automation (All Accounts)")
    print("=" * 60)
    
    async with async_playwright() as p:
        files = sorted(COOKIES_DIR.glob("*.txt"))
        for f in files:
            result = await try_account(p, f)
            if result:
                print(f"\n{'='*60}")
                print(f"  WINNER: {f.name}")
                print(f"  Notebook: {result}")
                print(f"{'='*60}")
                return
        
        print("\nAll accounts failed.")

if __name__ == "__main__":
    asyncio.run(main())
