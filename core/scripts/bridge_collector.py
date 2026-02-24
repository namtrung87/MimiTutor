import os
import shutil
import pypdf
import json
import re
from datetime import datetime

# --- Configuration ---
BASE_DIR = r"c:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant"
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
RESEARCH_BASE = os.path.join(BASE_DIR, "02_Research_Projects")
LOG_FILE = os.path.join(BASE_DIR, "research_inventory.json")

def extract_pdf_info(pdf_path):
    """Simple extraction of text and basic metadata from PDF."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text, "Academic Paper"
    except Exception as e:
        return None, str(e)

def extract_zai_info(md_path):
    """Extract info from Z.ai markdown exports."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Attempt to find a title or topic
            title_match = re.search(r"^#\s+(.*)", content, re.MULTILINE)
            topic = title_match.group(1) if title_match else "General Research"
            return content, topic
    except Exception as e:
        return None, str(e)

def get_project_folder(topic):
    """Map a topic to an existing or new project folder."""
    # Crude mapping logic - can be improved based on user feedback
    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip().replace(" ", "_")[:50]
    proj_path = os.path.join(RESEARCH_BASE, safe_topic)
    
    if not os.path.exists(proj_path):
        os.makedirs(os.path.join(proj_path, "raw"))
        os.makedirs(os.path.join(proj_path, "text"))
    
    return proj_path

def process_inbox():
    if not os.path.exists(INBOX_DIR):
        print("Inbox folder not found.")
        return

    files = [f for f in os.listdir(INBOX_DIR) if os.path.isfile(os.path.join(INBOX_DIR, f))]
    if not files:
        print("Inbox is empty.")
        return

    inventory = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            inventory = json.load(f)

    for filename in files:
        file_path = os.path.join(INBOX_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        print(f"Processing: {filename}")
        content = None
        topic = "General"

        if ext == ".pdf":
            content, topic = extract_pdf_info(file_path)
            topic = filename.replace(".pdf", "") # default for papers
        elif ext in [".md", ".txt"]:
            content, topic = extract_zai_info(file_path)
        
        if content:
            proj_dir = get_project_folder(topic)
            
            # Move raw file
            raw_dest = os.path.join(proj_dir, "raw", filename)
            shutil.move(file_path, raw_dest)
            
            # Save extracted text
            txt_filename = filename.rsplit('.', 1)[0] + ".txt"
            txt_dest = os.path.join(proj_dir, "text", txt_filename)
            with open(txt_dest, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update inventory
            entry = {
                "timestamp": datetime.now().isoformat(),
                "original_name": filename,
                "project": os.path.basename(proj_dir),
                "type": ext,
                "text_path": os.path.relpath(txt_dest, BASE_DIR)
            }
            inventory.append(entry)
            print(f"Successfully routed to {proj_dir}")
        else:
            print(f"Skipping {filename}: Could not extract content.")

    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=4)

if __name__ == "__main__":
    process_inbox()
