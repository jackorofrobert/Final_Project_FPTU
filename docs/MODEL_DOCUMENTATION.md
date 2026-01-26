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

---

## 1. Tổng Quan Hệ Thống

### 1.1 Mục tiêu của đề tài
Xây dựng hệ thống phát hiện email lừa đảo (phishing) sử dụng học máy (Machine Learning), có khả năng:
- Phân loại email thành **Lừa đảo (Phishing)** hoặc **Hợp lệ (Legitimate)** với độ chính xác cao
- Tự động trích xuất các đặc trưng từ nội dung email
- Cung cấp giao diện lập trình ứng dụng (API) và giao diện web để sử dụng

### 1.2 Đặc điểm nổi bật của hệ thống

| Đặc điểm | Mô tả |
|----------|-------|
| **Bộ nhớ tập dữ liệu** | Tự động lưu trữ và kết hợp nhiều tập dữ liệu khác nhau |
| **Tự động trích xuất đặc trưng** | Tự động phân tích và trích xuất các đặc trưng từ nội dung email |
| **Điểm đánh giá tổng hợp** | Kết hợp xác suất từ mô hình ML với các quy tắc đánh giá |
| **Phân loại đa cấp độ** | Chia thành 3 mức: An toàn, Nghi ngờ, Lừa đảo |

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
│  │   điểm = (xác_suất_mô_hình × 0.60)                         │ │
│  │        + (từ_khóa_khẩn_cấp × 0.15)                         │ │
│  │        + (rủi_ro_liên_kết × 0.15)                          │ │
│  │        + (rủi_ro_tên_miền × 0.10)                          │ │
│  │                                                            │ │
│  │ Thưởng tên miền tin cậy: Giảm 20% đến 40%                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Phân loại (ngưỡng = 0.6):                                  │ │
│  │   - điểm < 0.6          → AN TOÀN (Hợp lệ)                 │ │
│  │   - 0.6 ≤ điểm < 0.8    → NGHI NGỜ                         │ │
│  │   - điểm ≥ 0.8          → LỪA ĐẢO                          │ │
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

| Tiêu chí | Naive Bayes | Random Forest | XGBoost | Học sâu (Deep Learning) |
|----------|-------------|---------------|---------|-------------------------|
| **Độ chính xác** | Trung bình | Cao | **Rất cao** | Rất cao |
| **Tốc độ huấn luyện** | Rất nhanh | Trung bình | **Nhanh** | Chậm |
| **Khả năng giải thích** | Cao | Trung bình | **Trung bình** | Thấp |
| **Xử lý dữ liệu mất cân bằng** | Kém | Tốt | **Rất tốt** | Tốt |
| **Xem tầm quan trọng đặc trưng** | Không | Có | **Có** | Không |
| **Yêu cầu tài nguyên** | Thấp | Trung bình | **Trung bình** | Cao |

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

| Tham số | Giá trị | Giải thích |
|---------|---------|------------|
| `n_estimators` | 200 | Mô hình sử dụng 200 cây quyết định |
| `max_depth` | 6 | Mỗi cây có độ sâu tối đa 6 tầng, cân bằng giữa chi tiết và tổng quát |
| `learning_rate` | 0.1 | Tốc độ học vừa phải, tránh học quá nhanh gây overfitting |
| `subsample` | 0.8 | Mỗi cây chỉ dùng 80% dữ liệu, tăng tính đa dạng |
| `colsample_bytree` | 0.8 | Mỗi cây chỉ dùng 80% đặc trưng, giảm overfitting |

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

| Đặc trưng | Mô tả | Cách tính | Ý nghĩa trong phát hiện lừa đảo |
|-----------|-------|-----------|--------------------------------|
| `links_count` | Số lượng liên kết URL | Đếm bằng biểu thức chính quy | Email lừa đảo thường chứa nhiều liên kết |
| `urgent_keywords` | Có từ khóa khẩn cấp | Đối chiếu với danh sách | "khẩn cấp", "xác nhận", "tạm khóa" |
| `has_attachment` | Đề cập tệp đính kèm | Phát hiện mẫu | "tệp đính kèm", ".pdf", ".exe" |
| `body_length` | Độ dài nội dung | len(nội_dung) | Email lừa đảo thường ngắn hơn |
| `exclamation_count` | Số dấu chấm than | Đếm ký tự "!" | Email lừa đảo thường dùng nhiều dấu ! |

### 4.3 Đặc trưng danh mục (Categorical Features)

| Đặc trưng | Mô tả | Phương pháp mã hóa |
|-----------|-------|-------------------|
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
         công_thức = (xác_suất_mô_hình × 0.60)
                   + (từ_khóa_khẩn_cấp × 0.15)
                   + (rủi_ro_liên_kết × 0.15)
                   + (rủi_ro_tên_miền × 0.10)
         │
         ▼
Bước 4: Áp dụng thưởng tên miền tin cậy
         │
         Nếu tên miền người gửi tin cậy:
             điểm × 0.8 (giảm 20%)
         Nếu cả người gửi VÀ liên kết đều tin cậy:
             điểm × 0.6 (giảm 40%)
         │
         ▼
Bước 5: Phân loại cuối cùng
         │
         ├─ điểm < 0.6      → HỢP LỆ (An toàn)
         ├─ 0.6 ≤ điểm < 0.8 → NGHI NGỜ
         └─ điểm ≥ 0.8      → LỪA ĐẢO
```

### 6.2 Danh sách tên miền tin cậy

```python
TÊN_MIỀN_TIN_CẬY = [
    # Nền tảng tuyển dụng
    'linkedin.com', 'indeed.com', 'glassdoor.com', 'vietnamworks.com',
    
    # Công nghệ lớn
    'google.com', 'gmail.com', 'microsoft.com', 'outlook.com',
    'amazon.com', 'apple.com', 'facebook.com', 'meta.com',
    
    # Phát triển/Mạng xã hội
    'github.com', 'twitter.com', 'x.com', 'slack.com',
    
    # Thương mại điện tử Việt Nam
    'shopee.vn', 'lazada.vn', 'tiki.vn',
    
    # Thanh toán
    'paypal.com', 'stripe.com',
]
```

**Mục đích:** Giảm tỷ lệ dương tính giả (false positive) cho email từ các nguồn đáng tin cậy.

---

## 7. Kết Quả Đánh Giá Mô Hình

### 7.1 Thống kê tập dữ liệu

| Chỉ số | Giá trị |
|--------|---------|
| Tổng số email | 212.085 |
| Mẫu huấn luyện | 169.668 (80%) |
| Mẫu kiểm tra | 42.417 (20%) |
| Email hợp lệ | 113.096 (53,3%) |
| Email lừa đảo | 98.989 (46,7%) |

### 7.2 Hiệu suất mô hình

| Chỉ số | Giá trị | Giải thích |
|--------|---------|------------|
| **Độ chính xác (Accuracy)** | **96%** | Tỷ lệ dự đoán đúng tổng thể |
| **Điểm F1 (F1 Score)** | **0.9607** | Cân bằng giữa precision và recall |
| **Độ chính xác dương (Precision)** | 96% | Tỷ lệ email được gắn nhãn lừa đảo thực sự là lừa đảo |
| **Độ phủ (Recall)** | 96% | Tỷ lệ email lừa đảo được phát hiện |
| **Ngưỡng tối ưu** | 0.6 | Điểm cắt để phân loại |

### 7.3 Báo cáo phân loại chi tiết

```
                 Precision    Recall  F1-Score   Số mẫu

Hợp lệ (0)         0.96       0.96      0.96     22.619
Lừa đảo (1)        0.96       0.96      0.96     19.798

Độ chính xác                            0.96     42.417
Trung bình macro   0.96       0.96      0.96     42.417
Trung bình có trọng số 0.96   0.96      0.96     42.417
```

### 7.4 Quá trình tối ưu ngưỡng

| Ngưỡng | Điểm F1 | Ghi chú |
|--------|---------|---------|
| 0.30 | 0.9394 | |
| 0.35 | 0.9453 | |
| 0.40 | 0.9506 | |
| 0.45 | 0.9553 | |
| 0.50 | 0.9582 | Ngưỡng mặc định |
| 0.55 | 0.9603 | |
| **0.60** | **0.9607** | ✓ **Được chọn** |
| 0.65 | 0.9588 | |
| 0.70 | 0.9453 | |

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

| Phương thức | Đường dẫn | Mô tả |
|-------------|-----------|-------|
| POST | `/api/v1/predict` | Dự đoán một email |
| POST | `/api/v1/predict/batch` | Dự đoán nhiều email |
| GET | `/api/v1/health` | Kiểm tra trạng thái máy chủ |

---

## Phụ Lục

### A. Công nghệ sử dụng

| Tầng | Công nghệ |
|------|-----------|
| Học máy | scikit-learn, XGBoost |
| Xử lý văn bản | TF-IDF, BeautifulSoup |
| Giao diện lập trình | FastAPI |
| Giao diện người dùng | HTML, CSS, JavaScript |
| Xử lý dữ liệu | pandas, numpy |

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

*Tài liệu được tạo cho Đồ Án Tốt Nghiệp*
*Đề tài: Hệ Thống Phát Hiện Email Lừa Đảo sử dụng Học Máy*
