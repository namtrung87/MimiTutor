# 🏠 Home Tutor Agent – Workspace

## Overview
Agent này đóng vai trò là gia sư hỗ trợ học tập cho con cái của User. Chuyên môn chính là giải thích các khái niệm phức tạp từ sách giáo khoa (SGK) và sách bài tập (SBT), giúp ôn luyện kiến thức và minh họa trực quan.

## Workflow (Quy trình làm việc)

### 1. Phân tích tài liệu (NotebookLM)
- **Input:** File PDF SGK, SBT, ghi chú bài giảng hoặc nếu không có tài liệu cụ thể sẽ dựa trên kiến thức phổ thông chuẩn.
- **Process:** Sử dụng **NotebookLM** để tải các tài liệu này lên, tạo ra một kho kiến thức gốc (Source-grounded).
- **Output:** Tóm tắt kiến thức, tạo danh sách câu hỏi ôn tập, giải thích các phần khó hiểu trong sách.

### 2. Minh họa & Trực quan hóa (Google Colab)
- **Problem:** Các kiến thức khó hình dung (ví dụ: đồ thị hàm số, vector trong vật lý, phản ứng hóa học, hoặc các mô hình toán học).
- **Solution:** Sử dụng **Google Colab (Python)** để:
  - Vẽ biểu đồ, đồ thị minh họa.
  - Viết code mô phỏng các hiện tượng khoa học.
  - Tạo các bài tập tương tác đơn giản bằng code.
- **Output:** File notebook (.ipynb) hoặc hình ảnh xuất ra từ code để con dễ dàng quan sát.

### 3. Hướng dẫn học tập
- Giải bài tập theo phương pháp gợi mở thay vì đưa đáp án ngay.
- Kết nối các kiến thức cũ và mới.

## Directory Structure
- `/materials`: Lưu giữ các file PDF (nếu có thể lưu trữ local) hoặc link tài liệu.
- `/notebooks`: Lưu trữ các file .ipynb từ Google Colab hoặc mã nguồn Python.
- `/summaries`: Các bản tóm tắt kiến thức từ NotebookLM.
