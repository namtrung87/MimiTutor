import os
import glob
from docx import Document
import pdfplumber

RESEARCH_DIR = r"c:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\02_Research_Projects\Chatbot"

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"Error reading {file_path}: {e}"

def extract_text_from_pdf(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text
    except Exception as e:
        return f"Error reading {file_path}: {e}"

def main():
    files = glob.glob(os.path.join(RESEARCH_DIR, "*"))
    output_text = ""
    
    for file_path in files:
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        content = ""
        if ext == ".docx" and not filename.startswith("~$"): # Skip temp files
            print(f"Processing {filename}...")
            content = extract_text_from_docx(file_path)
        elif ext == ".pdf":
            print(f"Processing {filename}...")
            content = extract_text_from_pdf(file_path)
        else:
            continue
            
        output_text += f"\n\n{'='*20}\nFILE: {filename}\n{'='*20}\n\n{content}\n"

    with open("extracted_research_content.txt", "w", encoding="utf-8") as f:
        f.write(output_text)
    print("Done extracting text.")

if __name__ == "__main__":
    main()
