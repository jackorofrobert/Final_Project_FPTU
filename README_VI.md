# Hệ Thống Phát Hiện Email Phishing (AI-based)

## 1. Tổng Quan

Đây là hệ thống phát hiện email phishing sử dụng trí tuệ nhân tạo và học máy có giám sát.
Hệ thống có khả năng tự động đọc nhiều dataset, ghi nhớ dữ liệu đã huấn luyện trước đó,
và dự đoán phishing thông qua dòng lệnh mà không cần công cụ hỗ trợ.

---

## 2. Tính Năng Chính

- Tự động đọc toàn bộ dataset trong thư mục
- Ghi nhớ dữ liệu đã học thông qua lưu trữ dataset
- Huấn luyện lại trên dữ liệu tích luỹ
- Dự đoán phishing bằng PowerShell
- Xuất kết quả xác suất phishing
- Tự nhận diện cột text và nhãn (hoặc ép thủ công)

---

## 3. Cấu Trúc Dự Án

```
Final_FPTU/
├── src/
│ ├── train.py
│ ├── predict.py
│ ├── data_io.py
│ ├── text_cleaning.py
│ ├── features.py
│ └── config.py
│
├── data/
│ ├── incoming/ # New datasets (user input)
│ ├── history/ # Cached datasets (model memory)
│ └── runtime_cache/ # Internal use
│
├── models/
│ ├── model.joblib
│ └── metadata.json
│
└── README.md
```

---

## 4. Chiến Lược Ghi Nhớ Dataset

Mô hình không lưu trí nhớ dữ liệu bên trong.
Thay vào đó, hệ thống lưu trữ tất cả dataset đã huấn luyện trong thư mục lịch sử.

Mỗi lần huấn luyện:

- Dataset cũ được nạp lại
- Dataset mới được thêm vào
- Mô hình được huấn luyện lại từ đầu

Cách tiếp cận này đảm bảo không quên dữ liệu cũ và đúng nguyên lý học máy.

---

## 5. Huấn Luyện Mô Hình

Huấn luyện với toàn bộ dataset:
python -m src.train --data-dir data

Ép cột nếu dataset có cấu trúc lạ:
python -m src.train --data-dir data --text-col email_text --label-col is_phishing

---

## 6. Demo Dự Đoán

python -m src.predict --text "Urgent: verify your account now"

Kết quả hiển thị:

- Email có phải phishing hay không
- Xác suất phishing (%)

---

## 7. Kết Luận

Hệ thống phù hợp cho đồ án tốt nghiệp, cho phép mở rộng và tích hợp thực tế,
đáp ứng yêu cầu demo và đánh giá của giảng viên.
