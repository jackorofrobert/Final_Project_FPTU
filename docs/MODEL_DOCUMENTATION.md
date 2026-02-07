# Tài Liệu Kỹ Thuật: Hệ Thống Phát Hiện Email Lừa Đảo (Phishing)

## Mục Lục

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Kiến Trúc Hệ Thống](#2-kiến-trúc-hệ-thống)
3. [Lý Do Chọn Thuật Toán XGBoost](#3-lý-do-chọn-thuật-toán-xgboost)
4. [Kỹ Thuật Trích Xuất Đặc Trưng](#4-kỹ-thuật-trích-xuất-đặc-trưng-feature-engineering)
5. [Quy Trình Huấn Luyện Mô Hình](#5-quy-trình-huấn-luyện-mô-hình)
6. [Quy Trình Dự Đoán](#6-quy-trình-dự-đoán)
7. [Kết Quả Đánh Giá Mô Hình](#7-kết-quả-đánh-giá-mô-hình)
8. [Hướng Dẫn Sử Dụng](#8-hướng-dẫn-sử-dụng)
9. [So Sánh Với Các Mô Hình Baseline](#9-so-sánh-với-các-mô-hình-baseline)

---

## 1. Tổng Quan Hệ Thống

### 1.1 Mục tiêu của đề tài

Xây dựng hệ thống phát hiện email lừa đảo (phishing) sử dụng học máy (Machine Learning), có khả năng:

- Phân loại email thành **Lừa đảo (Phishing)** hoặc **Hợp lệ (Legitimate)** với độ chính xác cao
- Tự động trích xuất các đặc trưng từ nội dung email
- Cung cấp giao diện lập trình ứng dụng (API) và giao diện web để sử dụng

### 1.2 Đặc điểm nổi bật của hệ thống

| Đặc điểm                         | Mô tả                                                           |
| -------------------------------- | --------------------------------------------------------------- |
| **Bộ nhớ tập dữ liệu**           | Tự động lưu trữ và kết hợp nhiều tập dữ liệu khác nhau          |
| **Tự động trích xuất đặc trưng** | Tự động phân tích và trích xuất các đặc trưng từ nội dung email |
| **Điểm đánh giá tổng hợp**       | Kết hợp xác suất từ mô hình ML với các quy tắc đánh giá         |
| **Phân loại đa cấp độ**          | Chia thành 3 mức: An toàn, Nghi ngờ, Lừa đảo                    |

---

## 2. Kiến Trúc Hệ Thống

### 2.1 Sơ đồ tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│                      TẦNG ĐẦU VÀO                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Email thô   │  │ File email   │  │ Yêu cầu API (JSON)      │ │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TẦNG TIỀN XỬ LÝ                               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. Loại bỏ thẻ HTML (sử dụng BeautifulSoup)                │ │
│  │ 2. Chuẩn hóa văn bản (khoảng trắng, ký tự đặc biệt)        │ │
│  │ 3. Trích xuất đặc trưng:                                   │ │
│  │    - Số lượng liên kết (links_count)                       │ │
│  │    - Từ khóa khẩn cấp (urgent_keywords)                    │ │
│  │    - Đề cập tệp đính kèm (has_attachment)                  │ │
│  │    - Tên miền người gửi (sender_domain)                    │ │
│  │    - Độ dài nội dung, số dấu chấm than                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TẦNG XỬ LÝ HỌC MÁY                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Bộ chuyển đổi đặc trưng (ColumnTransformer):               │ │
│  │   ├─ Văn bản → TF-IDF (5000 đặc trưng, n-gram 1-2)         │ │
│  │   ├─ Số → Chuẩn hóa (StandardScaler)                       │ │
│  │   └─ Danh mục → Mã hóa one-hot (OneHotEncoder)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Bộ phân loại XGBoost                                       │ │
│  │   - Số cây quyết định: 200                                 │ │
│  │   - Độ sâu tối đa: 6                                       │ │
│  │   - Tốc độ học: 0.1                                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TẦNG HẬU XỬ LÝ                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Tính điểm tổng hợp (Ensemble Score):                       │ │
│  │   điểm = (xác_suất_mô_hình × 0.70)                         │ │
│  │        + (từ_khóa_khẩn_cấp × 0.12)                         │ │
│  │        + (rủi_ro_liên_kết × 0.105)                         │ │
│  │        + (rủi_ro_tên_miền × 0.075)                         │ │
│  │                                                            │ │
│  │ → Tổng = 100%, không có bonus riêng                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Phân loại (ngưỡng = 0.5):                                  │ │
│  │   - điểm < 0.5          → AN TOÀN (Hợp lệ)                 │ │
│  │   - 0.5 ≤ điểm < 0.7    → NGHI NGỜ                         │ │
│  │   - điểm ≥ 0.7          → LỪA ĐẢO                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        KẾT QUẢ                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ {                                                           ││
│  │   "dự_đoán": "lừa_đảo" | "nghi_ngờ" | "hợp_lệ",            ││
│  │   "độ_tin_cậy": 0.0 - 1.0,                                  ││
│  │   "điểm_tổng_hợp": 0.0 - 1.0,                               ││
│  │   "xác_suất_mô_hình": 0.0 - 1.0,                            ││
│  │   "yếu_tố_rủi_ro": { ... }                                  ││
│  │ }                                                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Lý Do Chọn Thuật Toán XGBoost

### 3.1 So sánh các thuật toán học máy

| Tiêu chí                         | Naive Bayes | Random Forest | XGBoost        | Học sâu (Deep Learning) |
| -------------------------------- | ----------- | ------------- | -------------- | ----------------------- |
| **Độ chính xác**                 | Trung bình  | Cao           | **Rất cao**    | Rất cao                 |
| **Tốc độ huấn luyện**            | Rất nhanh   | Trung bình    | **Nhanh**      | Chậm                    |
| **Khả năng giải thích**          | Cao         | Trung bình    | **Trung bình** | Thấp                    |
| **Xử lý dữ liệu mất cân bằng**   | Kém         | Tốt           | **Rất tốt**    | Tốt                     |
| **Xem tầm quan trọng đặc trưng** | Không       | Có            | **Có**         | Không                   |
| **Yêu cầu tài nguyên**           | Thấp        | Trung bình    | **Trung bình** | Cao                     |

### 3.2 Lý do chọn XGBoost

#### 1. **Hiệu suất vượt trội với dữ liệu dạng bảng**

XGBoost được thiết kế và tối ưu hóa đặc biệt cho dữ liệu có cấu trúc bảng - rất phù hợp với véc-tơ TF-IDF và các đặc trưng số học.

#### 2. **Xử lý tốt dữ liệu không cân bằng**

Trong thực tế, email lừa đảo thường chiếm tỷ lệ nhỏ hơn so với email hợp lệ. XGBoost có tham số `scale_pos_weight` giúp cân bằng hiệu quả.

#### 3. **Tích hợp sẵn cơ chế điều chuẩn (Regularization)**

- L1 (Lasso) và L2 (Ridge) regularization
- Giảm hiện tượng quá khớp (overfitting) một cách hiệu quả

#### 4. **Kỹ thuật Gradient Boosting Ensemble**

- Kết hợp nhiều bộ phân loại yếu (cây quyết định) thành một bộ phân loại mạnh
- Mỗi cây mới học từ sai sót của các cây trước đó
- Cải thiện liên tục độ chính xác qua mỗi vòng lặp

#### 5. **Khả năng xem tầm quan trọng đặc trưng**

Cung cấp thông tin chi tiết về tầm quan trọng của từng đặc trưng, giúp:

- Giải thích kết quả dự đoán
- Hiểu rõ các yếu tố ảnh hưởng đến việc phát hiện email lừa đảo

### 3.3 Cấu hình tham số XGBoost

```python
XGBClassifier(
    n_estimators=200,        # Số lượng cây quyết định
    max_depth=6,             # Độ sâu tối đa của mỗi cây
    learning_rate=0.1,       # Tốc độ học
    subsample=0.8,           # Tỷ lệ mẫu cho mỗi cây (80%)
    colsample_bytree=0.8,    # Tỷ lệ đặc trưng cho mỗi cây (80%)
    eval_metric="logloss",   # Hàm mất mát đánh giá
    random_state=42          # Hạt giống để tái tạo kết quả
)
```

| Tham số            | Giá trị | Giải thích                                                           |
| ------------------ | ------- | -------------------------------------------------------------------- |
| `n_estimators`     | 200     | Mô hình sử dụng 200 cây quyết định                                   |
| `max_depth`        | 6       | Mỗi cây có độ sâu tối đa 6 tầng, cân bằng giữa chi tiết và tổng quát |
| `learning_rate`    | 0.1     | Tốc độ học vừa phải, tránh học quá nhanh gây overfitting             |
| `subsample`        | 0.8     | Mỗi cây chỉ dùng 80% dữ liệu, tăng tính đa dạng                      |
| `colsample_bytree` | 0.8     | Mỗi cây chỉ dùng 80% đặc trưng, giảm overfitting                     |

---

## 4. Kỹ Thuật Trích Xuất Đặc Trưng (Feature Engineering)

### 4.1 Đặc trưng văn bản (TF-IDF)

**TF-IDF (Term Frequency - Inverse Document Frequency)** là kỹ thuật chuyển đổi văn bản thành véc-tơ số học.

**Công thức:**

```
TF-IDF(từ, tài_liệu) = TF(từ, tài_liệu) × IDF(từ, tập_dữ_liệu)

Trong đó:
- TF = Tần suất xuất hiện của từ trong tài liệu
- IDF = log(Tổng số tài liệu / Số tài liệu chứa từ đó)
```

**Cấu hình TF-IDF:**

```python
TfidfVectorizer(
    max_features=5000,      # Giữ lại 5000 từ/cụm từ quan trọng nhất
    ngram_range=(1, 2),     # Xét cả từ đơn và cụm 2 từ liên tiếp
    lowercase=True,         # Chuyển về chữ thường
    stop_words="english"    # Loại bỏ từ dừng (the, a, is, ...)
)
```

**Ví dụ:**
| Email | Các đặc trưng TF-IDF được trích xuất |
|-------|--------------------------------------|
| "Verify your account immediately" | verify: 0.5, account: 0.4, verify account: 0.3, immediately: 0.35 |
| "Meeting tomorrow at 3pm" | meeting: 0.6, tomorrow: 0.5, meeting tomorrow: 0.4 |

### 4.2 Đặc trưng số học (Numeric Features)

| Đặc trưng           | Mô tả                 | Cách tính                    | Ý nghĩa trong phát hiện lừa đảo          |
| ------------------- | --------------------- | ---------------------------- | ---------------------------------------- |
| `links_count`       | Số lượng liên kết URL | Đếm bằng biểu thức chính quy | Email lừa đảo thường chứa nhiều liên kết |
| `urgent_keywords`   | Có từ khóa khẩn cấp   | Đối chiếu với danh sách      | "khẩn cấp", "xác nhận", "tạm khóa"       |
| `has_attachment`    | Đề cập tệp đính kèm   | Phát hiện mẫu                | "tệp đính kèm", ".pdf", ".exe"           |
| `body_length`       | Độ dài nội dung       | len(nội_dung)                | Email lừa đảo thường ngắn hơn            |
| `exclamation_count` | Số dấu chấm than      | Đếm ký tự "!"                | Email lừa đảo thường dùng nhiều dấu !    |

### 4.3 Đặc trưng danh mục (Categorical Features)

| Đặc trưng       | Mô tả              | Phương pháp mã hóa             |
| --------------- | ------------------ | ------------------------------ |
| `sender_domain` | Tên miền người gửi | OneHotEncoder (mã hóa one-hot) |

### 4.4 Danh sách từ khóa khẩn cấp

```python
TỪ_KHÓA_KHẨN_CẤP = [
    'urgent', 'immediately', 'action required', 'act now', 'suspend',
    'verify', 'confirm', 'expire', 'limited time', 'final notice',
    'warning', 'alert', 'security', 'locked', 'disabled', 'blocked',
    'unauthorized', 'suspicious', 'unusual', 'violation', 'risk',
    '24 hours', '48 hours', 'deadline', 'asap', 'important'
]
```

**Giải thích:** Các từ khóa này thường được sử dụng trong email lừa đảo để tạo cảm giác cấp bách, khiến người nhận hành động vội vàng mà không suy nghĩ kỹ.

---

## 5. Quy Trình Huấn Luyện Mô Hình

### 5.1 Kiến trúc bộ nhớ tập dữ liệu (Dataset Memory)

**Mục đích:** Cho phép huấn luyện mô hình từ nhiều tập dữ liệu khác nhau mà không cần gộp thủ công.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ TậpDữLiệu_1.csv │     │ TậpDữLiệu_2.xlsx│     │ TậpDữLiệu_N.csv │
│ (mới)           │     │ (mới)           │     │ (mới)           │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────┬───────────┴───────────┬───────────┘
                     │                       │
                     ▼ Đặt vào thư mục       ▼
              ┌─────────────────────────────────────┐
              │         data/incoming/              │
              │  (Thư mục chứa dữ liệu mới)         │
              └──────────────┬──────────────────────┘
                             │
                             ▼ Băm (Hash) & Lưu bộ nhớ đệm
              ┌─────────────────────────────────────┐
              │         data/history/               │
              │  dataset_abc123.csv (đã xử lý)      │
              │  dataset_def456.csv (đã xử lý)      │
              │  dataset_ghi789.csv (đã xử lý)      │
              └──────────────┬──────────────────────┘
                             │
                             ▼ Tải tất cả dữ liệu
              ┌─────────────────────────────────────┐
              │    DataFrame kết hợp                │
              │  (Toàn bộ dữ liệu lịch sử)          │
              └──────────────┬──────────────────────┘
                             │
                             ▼
              ┌─────────────────────────────────────┐
              │       Huấn luyện mô hình            │
              └─────────────────────────────────────┘
```

### 5.2 Các bước huấn luyện chi tiết

```
Bước 1: Tải tập dữ liệu
         │
         ▼
Bước 2: Tự động phát hiện cột văn bản/nhãn
         │
         ▼
Bước 3: Trích xuất đặc trưng từ nội dung email
         ├─ links_count (số liên kết)
         ├─ urgent_keywords (từ khóa khẩn cấp)
         ├─ has_attachment (đề cập tệp đính kèm)
         ├─ sender_domain (tên miền người gửi)
         ├─ body_length (độ dài nội dung)
         └─ exclamation_count (số dấu chấm than)
         │
         ▼
Bước 4: Chuẩn hóa nhãn (0 = hợp lệ, 1 = lừa đảo)
         │
         ▼
Bước 5: Chia dữ liệu huấn luyện/kiểm tra (80%/20%)
         │
         ▼
Bước 6: Huấn luyện Pipeline
         ├─ Véc-tơ hóa TF-IDF cho văn bản
         ├─ Chuẩn hóa StandardScaler cho số
         ├─ Mã hóa OneHotEncoder cho danh mục
         └─ Bộ phân loại XGBoost
         │
         ▼
Bước 7: Tìm ngưỡng phân loại tối ưu
         │
         ▼
Bước 8: Đánh giá và lưu mô hình
```

### 5.3 Lệnh huấn luyện

```bash
python -m src.train --data-dir data --text-col body --label-col label
```

**Giải thích tham số:**

- `--data-dir data`: Thư mục chứa dữ liệu
- `--text-col body`: Tên cột chứa nội dung email
- `--label-col label`: Tên cột chứa nhãn (0/1)

---

## 6. Quy Trình Dự Đoán

### 6.1 Luồng xử lý dự đoán

```
Đầu vào: Văn bản email thô
         │
         ▼
Bước 1: Tiền xử lý
         ├─ Loại bỏ thẻ HTML
         ├─ Chuẩn hóa khoảng trắng
         └─ Trích xuất đặc trưng
         │
         ▼
Bước 2: Dự đoán bằng mô hình
         └─ Lấy xác suất P(lừa_đảo)
         │
         ▼
Bước 3: Tính điểm tổng hợp (Ensemble Score)
         │
         công_thức = (xác_suất_mô_hình × 0.70)
                   + (từ_khóa_khẩn_cấp × 0.12)
                   + (rủi_ro_liên_kết × 0.105)
                   + (rủi_ro_tên_miền × 0.075)
         │
         → Trust đã tích hợp trong Risk Scores (không cần bonus riêng)
         │
         ▼
Bước 4: Phân loại cuối cùng
         │
         ├─ điểm < 0.5      → HỢP LỆ (An toàn)
         ├─ 0.5 ≤ điểm < 0.7 → NGHI NGỜ
         └─ điểm ≥ 0.7      → LỪA ĐẢO
```

### 6.2 Phân loại tên miền (Domain Classification)

**Logic đơn giản:**

- **TRUSTED (0% risk):** Chỉ domain bạn tự thêm vào whitelist
- **SUSPICIOUS (50% risk):** Tất cả domain khác

```python
# File: src/config.py
TRUSTED_DOMAINS = [
    # Thêm domain của bạn ở đây
    # 'company.com',
    # 'partner.vn',
]
```

**Mục đích:** Cho phép người dùng tự quản lý whitelist, tất cả domain lạ đều được coi là đáng ngờ.

### 6.3 Phân loại liên kết (Link Classification)

| Loại       | Risk | Mô tả                            |
| ---------- | ---- | -------------------------------- |
| TRUSTED    | 0%   | Link đến domain trong whitelist  |
| SHORTENER  | 60%  | URL rút gọn (bit.ly, tinyurl...) |
| IP_BASED   | 90%  | Dùng IP thay domain              |
| SUSPICIOUS | 80%  | Có pattern lừa đảo trong URL     |
| NORMAL     | 10%  | Link bình thường                 |

---

## 7. Kết Quả Đánh Giá Mô Hình

### 7.1 Thống kê tập dữ liệu

| Chỉ số         | Giá trị         |
| -------------- | --------------- |
| Tổng số email  | 212.085         |
| Mẫu huấn luyện | 169.668 (80%)   |
| Mẫu kiểm tra   | 42.417 (20%)    |
| Email hợp lệ   | 113.096 (53,3%) |
| Email lừa đảo  | 98.989 (46,7%)  |

### 7.2 Giải Thích Chi Tiết Các Chỉ Số Đánh Giá

#### A. Confusion Matrix (Ma trận nhầm lẫn)

```
                              Dự đoán (Predicted)
                         Hợp lệ (0)    Phishing (1)
                        +-----------+-----------+
    Thực tế   Hợp lệ (0)|    TN     |    FP     |
    (Actual)            +-----------+-----------+
              Phish (1) |    FN     |    TP     |
                        +-----------+-----------+
```

| Ký hiệu | Tên đầy đủ     | Ý nghĩa                                   | Ví dụ                               |
| ------- | -------------- | ----------------------------------------- | ----------------------------------- |
| **TP**  | True Positive  | Phishing thực sự, dự đoán Phishing → ĐÚNG | Phát hiện đúng email lừa đảo        |
| **TN**  | True Negative  | Hợp lệ thực sự, dự đoán Hợp lệ → ĐÚNG     | Nhận diện đúng email an toàn        |
| **FP**  | False Positive | Hợp lệ thực sự, dự đoán Phishing → SAI    | Đánh nhầm email quan trọng vào spam |
| **FN**  | False Negative | Phishing thực sự, dự đoán Hợp lệ → SAI    | Bỏ sót email lừa đảo nguy hiểm      |

#### B. Các chỉ số đánh giá

| Chỉ số        | Công thức             | Ý nghĩa                                | Khi nào quan trọng?                   |
| ------------- | --------------------- | -------------------------------------- | ------------------------------------- |
| **Accuracy**  | (TP + TN) / Total     | % dự đoán đúng tổng thể                | Đánh giá tổng quan                    |
| **Precision** | TP / (TP + FP)        | Khi nói "Phishing", đúng bao nhiêu %?  | Không muốn đánh nhầm email quan trọng |
| **Recall**    | TP / (TP + FN)        | Bắt được bao nhiêu % phishing thực sự? | Không muốn bỏ sót email nguy hiểm     |
| **F1-Score**  | 2 × (P × R) / (P + R) | Cân bằng Precision và Recall           | So sánh tổng hợp các model            |

#### C. Minh họa với dữ liệu dự án

```
Confusion Matrix của XGBoost (trên 42,417 email test):

                              Dự đoán
                         Hợp lệ     Phishing
                        +--------+---------+
    Thực tế   Hợp lệ    | 21,714 |     905 |  ← 22,619 email hợp lệ
                        +--------+---------+
              Phishing  |    792 |  19,006 |  ← 19,798 email phishing
                        +--------+---------+

    Tính các chỉ số:
    - Accuracy  = (21,714 + 19,006) / 42,417 = 96%
    - Precision = 19,006 / (19,006 + 905) = 95.5%
    - Recall    = 19,006 / (19,006 + 792) = 96%
    - F1-Score  = 2 × (0.955 × 0.96) / (0.955 + 0.96) = 0.9607
```

### 7.3 Hiệu suất mô hình

| Chỉ số                             | Giá trị    | Giải thích                                           |
| ---------------------------------- | ---------- | ---------------------------------------------------- |
| **Độ chính xác (Accuracy)**        | **96%**    | Tỷ lệ dự đoán đúng tổng thể                          |
| **Điểm F1 (F1 Score)**             | **0.9607** | Cân bằng giữa precision và recall                    |
| **Độ chính xác dương (Precision)** | 96%        | Tỷ lệ email được gắn nhãn lừa đảo thực sự là lừa đảo |
| **Độ phủ (Recall)**                | 96%        | Tỷ lệ email lừa đảo được phát hiện                   |
| **Ngưỡng tối ưu**                  | 0.6        | Điểm cắt để phân loại                                |

### 7.4 Báo cáo phân loại chi tiết

```
                 Precision    Recall  F1-Score   Số mẫu

Hợp lệ (0)         0.96       0.96      0.96     22.619
Lừa đảo (1)        0.96       0.96      0.96     19.798

Độ chính xác                            0.96     42.417
Trung bình macro   0.96       0.96      0.96     42.417
Trung bình có trọng số 0.96   0.96      0.96     42.417
```

### 7.5 Quá trình tối ưu ngưỡng

| Ngưỡng   | Điểm F1    | Ghi chú         |
| -------- | ---------- | --------------- |
| 0.30     | 0.9394     |                 |
| 0.35     | 0.9453     |                 |
| 0.40     | 0.9506     |                 |
| 0.45     | 0.9553     |                 |
| 0.50     | 0.9582     | Ngưỡng mặc định |
| 0.55     | 0.9603     |                 |
| **0.60** | **0.9607** | ✓ **Được chọn** |
| 0.65     | 0.9588     |                 |
| 0.70     | 0.9453     |                 |

**Kết luận:** Ngưỡng 0.6 cho điểm F1 cao nhất, cân bằng tốt giữa việc phát hiện email lừa đảo và tránh báo động giả.

---

## 8. Hướng Dẫn Sử Dụng

### 8.1 Cài đặt môi trường

```bash
# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 8.2 Huấn luyện mô hình

```bash
# Bước 1: Đặt tập dữ liệu vào thư mục data/incoming/
# Bước 2: Chạy lệnh huấn luyện
python -m src.train --data-dir data --text-col body --label-col label
```

### 8.3 Dự đoán email

```bash
# Dự đoán từ văn bản trực tiếp
python -m src.predict --text "Verify your account now or it will be suspended"

# Dự đoán từ file
python -m src.predict --file samples/email.txt
```

### 8.4 Chạy máy chủ API

```bash
python run.py
# Máy chủ chạy tại: http://localhost:8000
```

### 8.5 Các điểm cuối API (API Endpoints)

| Phương thức | Đường dẫn               | Mô tả                       |
| ----------- | ----------------------- | --------------------------- |
| POST        | `/api/v1/predict`       | Dự đoán một email           |
| POST        | `/api/v1/predict/batch` | Dự đoán nhiều email         |
| GET         | `/api/v1/health`        | Kiểm tra trạng thái máy chủ |

---

## Phụ Lục

### A. Công nghệ sử dụng

| Tầng                 | Công nghệ             |
| -------------------- | --------------------- |
| Học máy              | scikit-learn, XGBoost |
| Xử lý văn bản        | TF-IDF, BeautifulSoup |
| Giao diện lập trình  | FastAPI               |
| Giao diện người dùng | HTML, CSS, JavaScript |
| Xử lý dữ liệu        | pandas, numpy         |

### B. Cấu trúc thư mục mã nguồn

```
src/
├── train.py         # Pipeline huấn luyện mô hình
├── predict.py       # Module dự đoán
├── features.py      # Kỹ thuật trích xuất đặc trưng
├── text_cleaning.py # Tiền xử lý văn bản
├── label_utils.py   # Chuẩn hóa nhãn
├── data_io.py       # Tải dữ liệu
└── config.py        # Cấu hình hệ thống
```

### C. Các câu hỏi thường gặp

**Q: Tại sao chọn TF-IDF thay vì Word Embedding (Word2Vec, BERT)?**

A: TF-IDF được chọn vì:

1. Nhanh và nhẹ, không cần GPU
2. Kết hợp tốt với XGBoost
3. Hiệu quả cao với bài toán phân loại văn bản ngắn
4. Dễ giải thích và debug

**Q: Mô hình có thể phát hiện các loại lừa đảo mới không?**

A: Có, nhờ học từ các mẫu (patterns) chung của email lừa đảo như:

- Từ khóa khẩn cấp
- Nhiều liên kết
- Tên miền đáng ngờ

**Q: Làm sao để cải thiện độ chính xác?**

A:

1. Thêm nhiều dữ liệu huấn luyện
2. Bổ sung các đặc trưng mới
3. Tinh chỉnh tham số XGBoost
4. Cập nhật danh sách từ khóa khẩn cấp

---

## 9. So Sánh Với Các Mô Hình Baseline

Để đánh giá hiệu quả của XGBoost, chúng tôi so sánh với 2 mô hình Baseline phổ biến: **Random Forest** và **Logistic Regression**.

### 9.0 Lý Do Chọn 2 Mô Hình Baseline

#### Tại sao chọn Logistic Regression?

| Lý do                | Giải thích                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------- |
| **Baseline chuẩn**   | Là mô hình cơ bản nhất cho bài toán phân loại nhị phân, được dùng làm mốc so sánh tối thiểu |
| **Đơn giản, nhanh**  | Thời gian train rất ngắn (~10s), phù hợp để kiểm tra nhanh                                  |
| **Dễ giải thích**    | Trọng số của từng feature có thể hiểu trực tiếp                                             |
| **Nguyên tắc Occam** | Nếu model phức tạp không thắng được Logistic Regression thì không đáng dùng                 |

#### Tại sao chọn Random Forest?

| Lý do                         | Giải thích                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| **Cùng họ Ensemble**          | Random Forest (Bagging) vs XGBoost (Boosting) → so sánh công bằng giữa 2 kỹ thuật Ensemble |
| **Phổ biến trong thực tế**    | Được sử dụng rộng rãi, nhiều người quen thuộc                                              |
| **Hiệu suất cao**             | Thường cho kết quả tốt với dữ liệu dạng bảng, là đối thủ xứng tầm với XGBoost              |
| **Không cần feature scaling** | Hoạt động tốt với TF-IDF mà không cần chuẩn hóa                                            |

#### Tại sao KHÔNG chọn các model khác?

| Model                 | Lý do không chọn                                                             |
| --------------------- | ---------------------------------------------------------------------------- |
| **Naive Bayes**       | Giả định các feature độc lập - không phù hợp với TF-IDF có tương quan        |
| **SVM**               | Chậm với dữ liệu lớn (>200k samples), khó tune hyperparameters               |
| **Deep Learning**     | Yêu cầu GPU, dữ liệu lớn hơn, khó giải thích - quá phức tạp cho bài toán này |
| **Decision Tree đơn** | Dễ overfitting, không đủ mạnh để làm baseline có ý nghĩa                     |

### 9.1 Giới Thiệu Các Mô Hình Baseline

#### A. Random Forest (Rừng Ngẫu Nhiên)

**Nguyên lý hoạt động:**

- Thuộc nhóm **Ensemble Learning** - phương pháp Bagging
- Xây dựng nhiều cây quyết định độc lập trên các mẫu dữ liệu ngẫu nhiên
- Kết quả cuối cùng = bỏ phiếu đa số từ tất cả các cây

```
     Dữ liệu gốc
         │
    ┌────┼────┐
    ↓    ↓    ↓
  Tree1 Tree2 Tree3   ← Train song song
    │    │    │
    └────┼────┘
         ↓
   Voting (Đa số)     ← Kết quả cuối
```

**Cấu hình trong dự án:**

```python
RandomForestClassifier(
    n_estimators=200,      # Số cây quyết định
    max_depth=10,          # Độ sâu tối đa
    min_samples_split=5,   # Số mẫu tối thiểu để chia nút
    min_samples_leaf=2,    # Số mẫu tối thiểu ở lá
    random_state=42
)
```

**Ưu điểm:**

- Ít bị overfitting hơn Decision Tree đơn lẻ
- Hoạt động tốt với dữ liệu có nhiều chiều
- Không cần feature scaling

**Nhược điểm:**

- Chậm hơn khi dự đoán (phải chạy qua nhiều cây)
- Khó giải thích hơn XGBoost

---

#### B. Logistic Regression (Hồi Quy Logistic)

**Nguyên lý hoạt động:**

- Mô hình tuyến tính cho bài toán phân loại nhị phân
- Sử dụng hàm sigmoid để chuyển đổi output thành xác suất (0-1)

**Công thức:**

```
P(y=1|x) = 1 / (1 + e^(-z))

Trong đó: z = w₀ + w₁x₁ + w₂x₂ + ... + wₙxₙ
```

**Cấu hình trong dự án:**

```python
LogisticRegression(
    max_iter=1000,         # Số vòng lặp tối đa
    random_state=42
)
```

**Ưu điểm:**

- Đơn giản, nhanh, dễ hiểu
- Cung cấp xác suất trực tiếp
- Tốt cho baseline comparison

**Nhược điểm:**

- Giả định quan hệ tuyến tính giữa features và output
- Không bắt được các patterns phức tạp

---

### 9.2 Bảng So Sánh Hiệu Suất

| Mô hình             | Accuracy | Precision | Recall  | F1-Score   | Thời gian Train |
| ------------------- | -------- | --------- | ------- | ---------- | --------------- |
| **XGBoost**         | **96%**  | **96%**   | **96%** | **0.9607** | ~60s            |
| Random Forest       | 95%      | 95%       | 95%     | 0.9520     | ~45s            |
| Logistic Regression | 91%      | 91%       | 91%     | 0.9100     | ~10s            |

> **Kết quả:** XGBoost cho hiệu suất tốt nhất với F1-Score = 0.9607

### 9.3 Phân Tích Chi Tiết

#### XGBoost vs Random Forest

| Tiêu chí            | XGBoost              | Random Forest   | Winner           |
| ------------------- | -------------------- | --------------- | ---------------- |
| F1-Score            | 0.9607               | 0.9520          | XGBoost (+0.87%) |
| Training Time       | ~60s                 | ~45s            | Random Forest    |
| Overfitting Control | L1+L2 Regularization | Bagging         | XGBoost          |
| Sequential Learning | Có (sửa lỗi)         | Không (độc lập) | XGBoost          |

**Nhận xét:**

- XGBoost có F1-Score cao hơn ~0.87% nhờ kỹ thuật Boosting (mỗi cây sửa lỗi cây trước)
- Random Forest train nhanh hơn vì các cây train song song
- Với dữ liệu email phishing, XGBoost bắt được các patterns phức tạp hơn

#### XGBoost vs Logistic Regression

| Tiêu chí            | XGBoost    | Logistic Regression | Winner              |
| ------------------- | ---------- | ------------------- | ------------------- |
| F1-Score            | 0.9607     | 0.9100              | XGBoost (+5.07%)    |
| Training Time       | ~60s       | ~10s                | Logistic Regression |
| Non-linear Patterns | Có         | Không               | XGBoost             |
| Interpretability    | Trung bình | Cao                 | Logistic Regression |

**Nhận xét:**

- XGBoost vượt trội với chênh lệch 5.07% F1-Score
- Logistic Regression nhanh nhất nhưng không bắt được quan hệ phi tuyến
- Email phishing có nhiều patterns phức tạp mà Logistic Regression không học được

---

### 9.4 Kết Luận Lựa Chọn Mô Hình

```
┌─────────────────────────────────────────────────────────────────┐
│                    KẾT LUẬN SO SÁNH MÔ HÌNH                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   🥇 Xếp hạng 1: XGBoost (F1 = 0.9607)                          │
│      → Được chọn cho production                                  │
│                                                                  │
│   🥈 Xếp hạng 2: Random Forest (F1 = 0.9520)                    │
│      → Baseline tốt, có thể dùng khi cần train nhanh            │
│                                                                  │
│   🥉 Xếp hạng 3: Logistic Regression (F1 = 0.9100)              │
│      → Baseline đơn giản, phù hợp cho quick prototyping         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Lý do chọn XGBoost:**

1. **Độ chính xác cao nhất** - F1-Score 0.9607, vượt trội so với các baseline
2. **Gradient Boosting** - Mỗi cây học từ sai sót của cây trước, cải thiện liên tục
3. **Regularization tích hợp** - L1 + L2 giúp tránh overfitting
4. **Feature Importance** - Có thể giải thích được feature nào quan trọng
5. **Xử lý tốt dữ liệu không cân bằng** - Phù hợp với bài toán phishing (tỷ lệ 53%/47%)

### 9.5 Script So Sánh Mô Hình

Để tự chạy so sánh, sử dụng script:

```bash
cd c:\Users\LTT\Desktop\Final_Project_FPTU
python scripts/compare_models.py
```

Script sẽ:

1. Load dataset từ `data/incoming/`
2. Train cả 3 mô hình trên cùng dữ liệu
3. Đánh giá và in bảng so sánh chi tiết

---

_Tài liệu được tạo cho Đồ Án Tốt Nghiệp_
_Đề tài: Hệ Thống Phát Hiện Email Lừa Đảo sử dụng Học Máy_
