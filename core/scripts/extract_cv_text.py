import pypdf
import os

def extract_pdf_txt(pdf_path, txt_path):
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
                
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Extracted {pdf_path} to {txt_path}")
    except Exception as e:
        print(f"Failed to extract {pdf_path}: {e}")

if __name__ == "__main__":
    cvs = [
        (r"E:\Dropbox\CV\UEB\CV - Nguyen Nam Trung - Lecturer.pdf", "cv_lecturer.txt"),
        (r"E:\Dropbox\CV\2021\CV - Nguyen Nam Trung.pdf", "cv_general.txt")
    ]
    for pdf, txt in cvs:
        extract_pdf_txt(pdf, txt)
