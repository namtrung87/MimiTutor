import pypdf
import os

def extract_pdf_txt(pdf_path, txt_path):
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return
    
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Extracted {pdf_path} to {txt_path}")

if __name__ == "__main__":
    folder = r"C:\Users\Trung Nguyen\Desktop\Working data"
    files = [
        "8. MCDM Fuzzy AHP-TOPSIS.pdf",
        "7. Fuzzy AHP.pdf",
        "6. Logistic Regression - WOE IV filter.pdf"
    ]
    for file in files:
        extract_pdf_txt(os.path.join(folder, file), file.replace(".pdf", ".txt"))
