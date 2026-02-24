import pandas as pd
import os

file_path = r"G:\My Drive\HAN Media\Accounting\Accounting database FY 2024.xlsx"
output_file = r"C:\Users\Trung Nguyen\Desktop\Antigravitiy\Orchesta assistant\financial_data_2024.txt"

print(f"Reading {file_path}...")

try:
    xls = pd.ExcelFile(file_path)
    
    with open(output_file, "w", encoding="utf-8") as f:
        # 1. Income Statement (KQHĐSXKD)
        sheet_kqkd = [s for s in xls.sheet_names if "KQHĐSXKD" in s]
        if sheet_kqkd:
            f.write(f"--- INCOME STATEMENT ({sheet_kqkd[0]}) ---\n")
            df = pd.read_excel(xls, sheet_name=sheet_kqkd[0])
            f.write(df.to_string())
            f.write("\n\n")
        else:
            f.write("--- INCOME STATEMENT NOT FOUND ---\n\n")

        # 2. Balance Sheet (CDKT)
        sheet_cdkt = [s for s in xls.sheet_names if "CDKT" in s]
        if sheet_cdkt:
            f.write(f"--- BALANCE SHEET ({sheet_cdkt[0]}) ---\n")
            df = pd.read_excel(xls, sheet_name=sheet_cdkt[0])
            f.write(df.to_string())
            f.write("\n\n")
        else:
            f.write("--- BALANCE SHEET NOT FOUND ---\n\n")

        # 3. Trial Balance (CDPS)
        sheet_cdps = [s for s in xls.sheet_names if "CDPS" in s]
        if sheet_cdps:
            f.write(f"--- TRIAL BALANCE ({sheet_cdps[0]}) ---\n")
            df = pd.read_excel(xls, sheet_name=sheet_cdps[0])
            f.write(df.to_string())
            f.write("\n\n")
        else:
            f.write("--- TRIAL BALANCE NOT FOUND ---\n\n")

    print(f"Data extracted to {output_file}")

except Exception as e:
    print(f"Error: {e}")
