import sys

try:
    with open(r"C:\Users\Trung Nguyen\Desktop\LLKH\luan_an_text.txt", "rb") as f:
        bytes = f.read(20)
        print(bytes)
except Exception as e:
    print(f"Error: {e}")
