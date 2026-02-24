import pandas as pd
import os

files = [
    r"G:\My Drive\HAN Media\Accounting\VAT Declaration.xlsx",
    r"G:\My Drive\HAN Media\DANH-SÁCH-NGƯỜI-LAO-ĐỘNG-HAN-MEDIA.xlsx"
]

for f in files:
    print(f"--- Reading {os.path.basename(f)} ---")
    if os.path.exists(f):
        try:
            df = pd.read_excel(f)
            print(df.to_string())
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("File not found.")
    print("\n")
