import pandas as pd
import os

files_to_inspect = [
    r"G:\My Drive\HAN Media\TM BCTC 2024.xlsx",
    r"G:\My Drive\HAN Media\Accounting\Accounting database FY 2024.xlsx"
]

for file_path in files_to_inspect:
    print(f"--- Inspecting {os.path.basename(file_path)} ---")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        continue

    try:
        xls = pd.ExcelFile(file_path)
        print("Sheet names:", xls.sheet_names)
        
        # Read first sheet and print head
        for sheet in xls.sheet_names[:2]: # First 2 sheets
            print(f"\nSheet: {sheet}")
            df = pd.read_excel(xls, sheet_name=sheet, nrows=5)
            print(df.to_string())
            print("\n")
            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
