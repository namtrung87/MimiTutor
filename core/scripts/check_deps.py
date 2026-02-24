try:
    import pandas
    print("pandas found")
except ImportError:
    print("pandas not found")

try:
    import openpyxl
    print("openpyxl found")
except ImportError:
    print("openpyxl not found")
