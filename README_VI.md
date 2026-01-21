# HỆ THỐNG PHÁT HIỆN EMAIL PHISHING (AI)

## 1. Tổng Quan

Đây là hệ thống phát hiện email phishing bằng AI sử dụng Machine Learning có giám sát.
Hệ thống được thiết kế theo hướng **kỹ sư hệ thống**, tập trung vào quản lý dữ liệu
thay vì chỉ tối ưu độ chính xác của mô hình.

Điểm nổi bật của hệ thống là kiến trúc **Dataset Memory**, cho phép huấn luyện từ
nhiều dataset khác nhau mà không cần gộp file thủ công và không mất dữ liệu cũ.

Hệ thống hoạt động hoàn toàn bằng **PowerShell / Terminal**, không phụ thuộc công cụ ngoài.

---

## 2. Tính Năng Chính

- Tự động đọc **toàn bộ dataset trong thư mục**
- Hỗ trợ CSV và Excel
- Ghi nhớ dataset cũ thông qua thư mục history
- Huấn luyện lại với dữ liệu tích luỹ (cũ + mới)
- Predict bằng dòng lệnh (text hoặc file)
- Xuất xác suất phishing để hỗ trợ quyết định
- Tự động nhận diện và chuẩn hoá cột text và label
- Xử lý tốt dataset không đồng nhất trong thực tế

---

## 3. Cấu Trúc Dự Án

```
Final_Project_FPTU/
├── src/
│   ├── __init__.py
│   ├── train.py
│   ├── predict.py
│   ├── features.py
│   ├── data_io.py
│   ├── label_utils.py
│   └── text_cleaning.py
│
├── data/
│   ├── incoming/         # Dataset mới
│   ├── history/          # Dataset đã cache (ghi nhớ)
│   └── runtime_cache/    # Dự phòng mở rộng
│
├── models/
│   ├── model.joblib
│   └── metadata.json
│
├── samples/
├── README.md
└── README_VI.md
```

---

## 4. Chiến Lược Xử Lý Dataset

### 4.1 Tự Động Nạp Dataset

Hệ thống tự động quét thư mục `data/incoming/` và đọc **tất cả dataset hợp lệ**
mà không cần gộp file thủ công.

Định dạng hỗ trợ:
- CSV
- Excel (.xlsx)

Dataset chỉ được gộp **trong bộ nhớ khi train**, đảm bảo quản lý dữ liệu sạch.

---

### 4.2 Dataset Memory (Ghi Nhớ Dữ Liệu Lịch Sử)

Model **không tự ghi nhớ dữ liệu cũ**.
Việc ghi nhớ dataset được thực hiện ở **cấp hệ thống** thông qua thư mục `data/history/`.

Quy trình:
1. Dataset mới được cache vào `history/`
2. Khi train, toàn bộ dataset lịch sử được load
3. Model được huấn luyện lại từ đầu với dữ liệu tích luỹ

Thiết kế này phù hợp với thực tế MLOps.

---

## 5. Huấn Luyện Mô Hình

### 5.1 Huấn Luyện Với Toàn Bộ Dataset

```bash
python -m src.train --data-dir data --text-col body --label-col label
```

### 5.2 Ép Cột Text và Label (Dataset Lạ)

```bash
python -m src.train --data-dir data --text-col email_text --label-col is_phishing
```

---

## 6. Kết Quả Huấn Luyện

Sau khi train, hệ thống sinh ra:

```
models/
├── model.joblib
└── metadata.json
```

Metadata bao gồm:
- Số lượng dataset
- Số lượng mẫu
- Phân bố nhãn
- Các chỉ số đánh giá

---

## 7. Demo Dự Đoán

### Dự đoán email phishing

```bash
python -m src.predict --text "Urgent: Verify your bank account immediately"
```

### Dự đoán email hợp lệ

```bash
python -m src.predict --text "Team meeting at 10 AM tomorrow"
```

### Dự đoán từ file email

```bash
python -m src.predict --file samples/phishing.txt
```

### Xuất JSON (tích hợp tool khác)

```bash
python -m src.predict --file samples/phishing.txt --json
```

---

## 8. Kiến Trúc Mô Hình AI

- Tiền xử lý văn bản
- Trích xuất đặc trưng TF-IDF
- Phân loại bằng XGBoost

**Lý do chọn XGBoost:**
- Phù hợp dữ liệu text dạng sparse
- Huấn luyện nhanh
- Ít overfitting
- Phù hợp đồ án học thuật

---

## 9. Hạn Chế

- Chỉ hỗ trợ batch learning
- Cần train lại khi có dữ liệu mới
- Email marketing dễ false positive
- Dataset chủ yếu tiếng Anh

---

## 10. Kết Luận

Hệ thống phát hiện email phishing này thể hiện:
- Thiết kế hệ thống đúng hướng
- Quản lý dataset thực tế hiệu quả
- Phù hợp cho đồ án tốt nghiệp và demo học thuật

Trọng tâm không chỉ là độ chính xác,
mà là **tư duy kỹ sư và kiến trúc hệ thống**.
