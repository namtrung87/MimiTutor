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
    scientific_cv = [
        (r"C:\Users\Trung Nguyen\Desktop\LLKH\Mau 04_06.LLKH_Nguyen Nam Trung.pdf", "llkh_scientific.txt"),
        (r"C:\Users\Trung Nguyen\Desktop\LLKH\6. Ly lich khoa hoc - NS.pdf", "llkh_ns.txt")
    ]
    for pdf, txt in scientific_cv:
        extract_pdf_txt(pdf, txt)
