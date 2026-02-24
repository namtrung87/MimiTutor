import pandas as pd
import os

root_dir = r"G:\My Drive\HAN Media"
print(f"Listing {root_dir}:")
try:
    for f in os.listdir(root_dir):
        if "TM BCTC 2024" in f:
            print(f"Found: '{f}' - Path: {os.path.join(root_dir, f)}")
except Exception as e:
    print(f"Error listing dir: {e}")

file_path = r"G:\My Drive\HAN Media\Accounting\Accounting database FY 2024.xlsx"
print(f"\n--- Inspecting {os.path.basename(file_path)} ---")

try:
    xls = pd.ExcelFile(file_path)
    print("Sheet names:", xls.sheet_names)
    
    # Identify likely data sheets
    data_sheets = [s for s in xls.sheet_names if "DATA" in s.upper() or "CDPS" in s.upper() or "NKC" in s.upper()]
    print("Potential data sheets:", data_sheets)
    
    for sheet in data_sheets[:3]: # Inspect first 3 potential data sheets
        print(f"\nSheet: {sheet}")
        df = pd.read_excel(xls, sheet_name=sheet, nrows=10)
        print(df.to_string())
        print("\n")
        
except Exception as e:
    print(f"Error reading {file_path}: {e}")
