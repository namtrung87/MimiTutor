import sys

try:
    with open(r"C:\Users\Trung Nguyen\Desktop\LLKH\luan_an_text.txt", "r", encoding="utf-8-sig") as f:
        content = f.read(5000)
        print(content)
except Exception as e:
    print(f"Error reading dissertation: {e}")
