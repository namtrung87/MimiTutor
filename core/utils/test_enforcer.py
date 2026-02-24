import os
import sys
from pathlib import Path

def check_test_coverage(code_dir="core/agents", test_dir="tests"):
    """
    Kiểm tra xem các file .py trong code_dir có file test tương ứng trong test_dir hay không.
    """
    root = Path(__file__).parent.parent.parent
    code_path = root / code_dir
    test_path = root / test_dir
    
    missing_tests = []
    
    for py_file in code_path.glob("**/*.py"):
        if py_file.name == "__init__.py":
            continue
            
        # Match pattern: test_{filename}.py or {filename}_test.py
        test_file_name_1 = f"test_{py_file.name}"
        test_file_name_2 = py_file.name.replace(".py", "_test.py")
        
        found = False
        for t_file in test_path.glob("**/*.py"):
            if t_file.name == test_file_name_1 or t_file.name == test_file_name_2:
                found = True
                break
        
        if not found:
            missing_tests.append(str(py_file.relative_to(root)))
            
    return missing_tests

if __name__ == "__main__":
    print("--- [Test Enforcer] Checking for missing Unit Tests ---")
    missing = check_test_coverage()
    
    if missing:
        print("\n⚠️  CẢNH BÁO: Các file sau thiếu Unit Test tương ứng:")
        for m in missing:
            print(f"  - {m}")
        print("\n[Vibe Coding Rule] Vui lòng tạo file test trước khi commit code mới.")
        # sys.exit(1) # Uncomment to block builds
    else:
        print("\n✅ Tuyệt vời! Tất cả các module đều có file test đi kèm.")
