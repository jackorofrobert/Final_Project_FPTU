# Hướng Dẫn Trích Xuất Đặc Trưng (Feature Extraction)

> **📚 Tài liệu kỹ thuật cho nhóm** - Giải thích chi tiết cách trích xuất các đặc trưng từ email và cách tính ngưỡng (threshold) tối ưu trong dự án.

---

## Mục Lục

1. [Feature Engineering là gì?](#1-feature-engineering-là-gì)
2. [Các loại đặc trưng trong dự án](#2-các-loại-đặc-trưng-trong-dự-án)
3. [1. Đặc trưng văn bản - TF-IDF](#3-đặc-trưng-văn-bản---tf-idf)
4. [2. Đặc trưng số học (Numeric)](#4-đặc-trưng-số-học-numeric)
5. [3. Đặc trưng danh mục (Categorical)](#5-đặc-trưng-danh-mục-categorical)
6. [Cách tính Threshold (Ngưỡng)](#6-cách-tính-threshold-ngưỡng)
7. [Ensemble Score - Điểm tổng hợp](#7-ensemble-score---điểm-tổng-hợp)
8. [Code Reference](#8-code-reference)

---

## 1. Feature Engineering là gì?

### 1.1 Định nghĩa

**Feature Engineering (Kỹ thuật trích xuất đặc trưng)** là quá trình chuyển đổi dữ liệu thô thành các đặc trưng (features) mà mô hình Machine Learning có thể học được.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Dữ liệu thô   │ ──▶ │ Feature         │ ──▶ │  Vector số học  │
│   (Email text)  │     │ Engineering     │     │  [0.5, 1, 3, 0] │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1.2 Tại sao quan trọng?

> 💡 **"Feature Engineering is the key"** - Nhiều cuộc thi ML thắng nhờ features tốt, không phải thuật toán phức tạp.

Máy tính không hiểu văn bản trực tiếp. Ta cần chuyển thành số:

- "urgent" → không hiểu
- urgent_keywords = 1 → hiểu được!

---

## 2. Các loại đặc trưng trong dự án

### 2.1 Tổng quan pipeline

```
     Email thô
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│                   FEATURE EXTRACTION                        │
├────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────┐                                       │
│   │   TEXT          │──▶ TF-IDF Vectorizer ──▶ 5000 features│
│   │   (nội dung)    │                                       │
│   └─────────────────┘                                       │
│                                                             │
│   ┌─────────────────┐                                       │
│   │   NUMERIC       │──▶ StandardScaler ──▶ 5 features      │
│   │   (số học)      │    - links_count                      │
│   │                 │    - urgent_keywords                  │
│   │                 │    - has_attachment                   │
│   │                 │    - body_length                      │
│   │                 │    - exclamation_count                │
│   └─────────────────┘                                       │
│                                                             │
│   ┌─────────────────┐                                       │
│   │   CATEGORICAL   │──▶ OneHotEncoder ──▶ N features       │
│   │   (danh mục)    │    - sender_domain                    │
│   └─────────────────┘                                       │
│                                                             │
└────────────────────────────────────────────────────────────┘
         │
         ▼
   Vector tổng hợp → XGBoost Classifier
```

### 2.2 Danh sách đầy đủ các features

| STT | Feature             | Loại        | Mô tả                           | Phương pháp trích xuất   |
| --- | ------------------- | ----------- | ------------------------------- | ------------------------ |
| 1   | `text`              | Text        | Nội dung email đã tiền xử lý    | TF-IDF (5000 features)   |
| 2   | `links_count`       | Numeric     | Số lượng URL trong email        | Đếm bằng Regex           |
| 3   | `urgent_keywords`   | Numeric     | Có chứa từ khóa khẩn cấp? (0/1) | Đối chiếu danh sách      |
| 4   | `has_attachment`    | Numeric     | Có đề cập file đính kèm? (0/1)  | Pattern matching         |
| 5   | `body_length`       | Numeric     | Độ dài nội dung (ký tự)         | len(text)                |
| 6   | `exclamation_count` | Numeric     | Số dấu chấm than (!)            | Đếm ký tự                |
| 7   | `sender_domain`     | Categorical | Tên miền người gửi              | Extract từ email address |

---

## 3. Đặc trưng văn bản - TF-IDF

### 3.1 TF-IDF là gì?

**TF-IDF** = **T**erm **F**requency - **I**nverse **D**ocument **F**requency

Là kỹ thuật chuyển văn bản thành vector số, đánh giá tầm quan trọng của từ trong tài liệu.

### 3.2 Công thức chi tiết

```
TF-IDF(từ, tài_liệu, corpus) = TF(từ, tài_liệu) × IDF(từ, corpus)
```

#### Term Frequency (TF)

```
TF(từ, tài_liệu) = Số lần từ xuất hiện trong tài liệu / Tổng số từ trong tài liệu
```

**Ví dụ:**

```
Email: "Verify your account. Please verify now."
Total words: 6

TF("verify") = 2/6 = 0.33
TF("account") = 1/6 = 0.17
TF("please") = 1/6 = 0.17
```

#### Inverse Document Frequency (IDF)

```
IDF(từ, corpus) = log(Tổng số tài liệu / Số tài liệu chứa từ đó)
```

**Ý nghĩa:** Từ xuất hiện ở nhiều tài liệu → IDF thấp → ít quan trọng

**Ví dụ với corpus 100,000 emails:**

```
"the" xuất hiện trong 99,000 emails → IDF = log(100000/99000) = 0.01 (rất thấp)
"verify" xuất hiện trong 5,000 emails → IDF = log(100000/5000) = 3.0 (cao)
"immediately" xuất hiện trong 2,000 emails → IDF = log(100000/2000) = 3.9 (rất cao)
```

#### Tính TF-IDF

```
TF-IDF("verify") = 0.33 × 3.0 = 0.99
TF-IDF("the") = 0.17 × 0.01 = 0.0017
```

> 💡 **Kết luận:** "verify" quan trọng hơn "the" trong việc phát hiện phishing!

### 3.3 Cấu hình TF-IDF trong dự án

```python
# File: src/features.py
TfidfVectorizer(
    max_features=5000,      # Giữ 5000 từ/cụm từ quan trọng nhất
    ngram_range=(1, 2),     # Unigram + Bigram
    lowercase=True,         # Chuyển về chữ thường
    stop_words="english"    # Loại bỏ stop words (the, is, a, ...)
)
```

**Tại sao chọn con số 5000? (Rationale)**

1. **Sự cân bằng (Trade-off):** Nếu chọn quá ít (ví dụ 500), mô hình sẽ bỏ sót các từ khóa chuyên biệt của phishing. Nếu chọn quá nhiều (ví dụ 50,000), ma trận dữ liệu sẽ cực kỳ thưa thớt (sparse), làm chậm tốc độ huấn luyện và dễ gây ra lỗi **Overfitting** (mô hình học thuộc lòng các từ hiếm thay vì học đặc điểm chung).
2. **Quy luật 80/20:** Trong ngôn ngữ học, các từ quan trọng nhất thường nằm trong top 3000-5000 từ phổ biến nhất. Sau ngưỡng này, các từ còn lại thường là lỗi chính tả hoặc từ cực hiếm, không đóng góp nhiều vào độ chính xác.
3. **Hiệu năng hệ thống (Performance):** Vocabulary có 5000 từ giúp file `model.joblib` có kích thước vừa phải, load lên RAM nhanh và tốc độ dự đoán (inference) gần như tức thì khi chạy trên Web API.
4. **Kết quả thực nghiệm:** Qua thực tế chạy `compare_models.py`, mức 5000 features cho kết quả F1-Score tối ưu nhất trên bộ dữ liệu Balanced Dataset.

### 3.4 N-gram là gì?

```
Email: "Verify your account immediately"

Unigram (n=1): ["verify", "your", "account", "immediately"]
Bigram (n=2):  ["verify your", "your account", "account immediately"]

→ Dự án dùng cả hai (ngram_range=(1, 2))
```

**Tại sao dùng Bigram?**

- "account" đơn lẻ ít ý nghĩa
- "verify account" rõ ràng là dấu hiệu phishing

### 3.5 Ví dụ output TF-IDF

```
Input: "Urgent: Verify your PayPal account immediately"

Output vector (sparse, chỉ hiện một số):
{
  "urgent": 0.45,
  "verify": 0.52,
  "paypal": 0.61,
  "account": 0.38,
  "immediately": 0.48,
  "verify account": 0.55,
  ...
  # 5000 chiều tổng cộng
}
```

---

## 4. Đặc trưng số học (Numeric)

### 4.1 links_count - Đếm số liên kết

```python
# File: src/text_cleaning.py

import re

def count_urls(text: str) -> int:
    """Đếm số lượng URL trong văn bản"""
    url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    return len(urls)

# Ví dụ:
text = "Click here: https://fake.com or https://phishing.net"
count_urls(text)  # Output: 2
```

**Lý do lựa chọn (Rationale):**

- **Dấu hiệu kỹ thuật:** Hacker thường chèn nhiều link ẩn (hidden links) hoặc các nút CTA (Call to Action) giả mạo để điều hướng người dùng.
- **Phân phối thống kê:** Trong dataset thực tế, email giao dịch bình thường hiếm khi có quá 3 liên kết, trong khi email phishing thường dàn trải link ở khắp mọi nơi (Header, Body, Footer) để tăng tỷ lệ người dùng click nhầm.

**Thang điểm rủi ro (Ensemble components):**
| Số link | Mức độ rủi ro | Trọng số đóng góp |
|---------|---------------|-------------------|
| 0 | 0.0 (An toàn) | 0% |
| 1 | 0.2 (Thấp) | Tăng nhẹ rủi ro |
| 2-3 | 0.4 (Trung bình) | Nghi ngờ |
| 4-5 | 0.6 (Cao) | Đáng báo động |
| >5 | 0.8 (Rất cao) | Cảnh báo đỏ |

### 4.2 urgent_keywords - Từ khóa khẩn cấp

```python
# File: src/text_cleaning.py

URGENT_KEYWORDS = [
    'urgent', 'immediately', 'action required', 'act now', 'suspend',
    'verify', 'confirm', 'expire', 'limited time', 'final notice',
    'warning', 'alert', 'security', 'locked', 'disabled', 'blocked',
    'unauthorized', 'suspicious', 'unusual', 'violation', 'risk',
    '24 hours', '48 hours', 'deadline', 'asap', 'important'
]

def detect_urgent_keywords(text: str) -> int:
    """Kiểm tra có từ khóa khẩn cấp không (0 hoặc 1)"""
    text_lower = text.lower()
    for keyword in URGENT_KEYWORDS:
        if keyword in text_lower:
            return 1
    return 0
```

**Lý do lựa chọn (Rationale):**

- **Tâm lý học hành vi (Social Engineering):** Phishing dựa trên việc tạo ra "Sự khan hiếm" (Scarcity) và "Sự khẩn cấp" (Urgency). Bằng cách thông báo tài khoản bị khóa trong 24h, kẻ tấn công ép nạn nhân phải hành động theo bản năng mà bỏ qua các bước kiểm tra an toàn.
- **Đặc trưng ngôn ngữ:** Tập hợp các từ này là các "Anchor words" (từ neo) xuất hiện với tần suất cực cao trong các chiến dịch phishing nổi tiếng (Paypal, Apple ID).

### 4.3 has_attachment - Đề cập file đính kèm

```python
# File: src/text_cleaning.py

ATTACHMENT_PATTERNS = [
    'attachment', 'attached', 'enclosed',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.rar', '.exe', '.scr',
    'download the file', 'open the attachment'
]

def detect_attachment_mention(text: str) -> int:
    """Kiểm tra có đề cập file đính kèm không"""
    text_lower = text.lower()
    for pattern in ATTACHMENT_PATTERNS:
        if pattern in text_lower:
            return 1
    return 0
```

**Lý do lựa chọn (Rationale):**

- **Véc-tơ tấn công (Attack Vector):** Bên cạnh link, file đính kèm là con đường chính để phát tán Malware/Ransomware.
- **Lọc sơ bộ:** Việc phát hiện sớm các từ khóa liên quan đến file thực thi (.exe, .scr) hoặc file nén (.zip) giúp hệ thống cảnh giác cao độ ngay cả khi model chưa phân loại xong phần text.

### 4.4 body_length - Độ dài nội dung

```python
def length_chars(text: str) -> int:
    """Trả về độ dài văn bản (số ký tự)"""
    return len(str(text))
```

**Lý do lựa chọn (Rationale):**

- **Mô hình hóa dữ liệu:** Qua phân tích dataset, email phishing thường có xu hướng **cực ngắn** (chỉ có link và câu lệnh) hoặc **cực dài** (giả mạo điều khoản dịch vụ). Email cá nhân/công việc bình thường thường nằm ở dải độ dài trung bình (200-800 ký tự). Trích xuất `body_length` giúp XGBoost tìm ra các "ngưỡng" bất thường này.

### 4.5 exclamation_count - Số dấu chấm than

```python
def exclamation_count(text: str) -> int:
    """Đếm số dấu chấm than"""
    return str(text).count('!')
```

**Lý do lựa chọn (Rationale):**

- **Cảm xúc hóa (Sentiment Analysis):** Dấu chấm than liên tục (`!!!`) thể hiện sự kích động hoặc đe dọa. Email doanh nghiệp hoặc thông báo từ ngân hàng thật thường rất trung lập và hiếm khi dùng quá 1 dấu chấm than. Đây là đặc trưng "nhiễu" nhưng lại rất hiệu quả để nhận diện các mail lừa đảo trúng thưởng hoặc đe dọa khóa tài khoản.

### 4.6 StandardScaler - Chuẩn hóa dữ liệu số

```python
# Tại sao cần chuẩn hóa?
# - links_count: 0 - 50
# - body_length: 0 - 10000
# → Scale khác nhau, model khó học

from sklearn.preprocessing import StandardScaler

# StandardScaler: chuyển về mean=0, std=1
scaler = StandardScaler()
scaled_features = scaler.fit_transform(numeric_features)
```

**Công thức:**

```
z = (x - mean) / std_deviation
```

---

## 5. Đặc trưng danh mục (Categorical)

### 5.1 sender_domain - Tên miền người gửi

```python
# File: src/text_cleaning.py

import re

def extract_sender_domain(text: str) -> str:
    """Trích xuất tên miền từ địa chỉ email trong văn bản"""
    email_pattern = r'[\w\.-]+@([\w\.-]+)'
    match = re.search(email_pattern, text)
    if match:
        return match.group(1).lower()
    return "unknown"

# Ví dụ:
text1 = "From: support@paypal.com"
extract_sender_domain(text1)  # Output: "paypal.com"

text2 = "From: urgent@secure-paypa1.xyz"
extract_sender_domain(text2)  # Output: "secure-paypa1.xyz"
```

### 5.2 One-Hot Encoding

Vì domain là categorical (không phải số), cần chuyển thành số:

```python
# Input domains: ["gmail.com", "paypal.com", "unknown"]

# One-Hot Encoding output:
#              gmail.com  paypal.com  unknown
# Email 1          1          0          0
# Email 2          0          1          0
# Email 3          0          0          1
```

### 5.3 Trusted Domains List

```python
# File: src/config.py

TRUSTED_DOMAINS = [
    # Big Tech
    'google.com', 'gmail.com', 'microsoft.com', 'outlook.com',
    'amazon.com', 'apple.com', 'facebook.com', 'meta.com',

    # Job platforms
    'linkedin.com', 'indeed.com', 'vietnamworks.com',

    # Vietnam E-commerce
    'shopee.vn', 'lazada.vn', 'tiki.vn',

    # Payment
    'paypal.com', 'stripe.com',
]
```

**Tại sao quan trọng?**

- Email từ trusted domain → Giảm điểm rủi ro
- Email từ "paypa1-secure.xyz" → Tăng điểm rủi ro

---

## 6. Cách tính Threshold (Ngưỡng)

### 6.1 Threshold là gì?

**Threshold (Ngưỡng)** là điểm cắt để quyết định phân loại.

```
Xác suất model output: 0.72% phishing

If threshold = 0.5:
    → 0.72 >= 0.5 → PHISHING

If threshold = 0.8:
    → 0.72 < 0.8 → LEGITIMATE
```

### 6.2 Tại sao không dùng 0.5 mặc định?

```
Threshold thấp (0.3):
    - Bắt nhiều phishing hơn (Recall cao)
    - Nhưng cũng bắt nhầm email hợp lệ nhiều hơn (Precision thấp)

Threshold cao (0.8):
    - Ít bắt nhầm email hợp lệ (Precision cao)
    - Nhưng có thể bỏ sót phishing (Recall thấp)
```

### 6.3 Phương pháp tìm Threshold tối ưu

```python
# File: src/train.py (lines 251-267)

# Grid Search trên tập validation
print("Finding optimal threshold...")
y_proba = pipeline.predict_proba(X_test)[:, 1]

best_threshold = 0.5
best_f1 = 0.0

# Thử các threshold từ 0.3 đến 0.7
for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]:
    y_pred_thresh = (y_proba >= threshold).astype(int)
    f1 = f1_score(y_test, y_pred_thresh, average='weighted')
    print(f"  Threshold {threshold:.2f}: F1 = {f1:.4f}")
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = threshold

print(f">>> Optimal threshold: {best_threshold} (F1 = {best_f1:.4f})")
```

### 6.4 Kết quả Grid Search trong dự án

| Threshold | F1-Score   | Ghi chú        |
| --------- | ---------- | -------------- |
| 0.30      | 0.9394     | Too low        |
| 0.35      | 0.9453     |                |
| 0.40      | 0.9506     |                |
| 0.45      | 0.9553     |                |
| 0.50      | 0.9582     | Default        |
| 0.55      | 0.9603     |                |
| **0.60**  | **0.9607** | ✅ **OPTIMAL** |
| 0.65      | 0.9588     |                |
| 0.70      | 0.9453     | Too high       |

> 💡 **Kết luận:** Threshold = 0.6 cho F1-Score cao nhất (0.9607)

### 6.5 Minh họa trực quan

```
               Threshold = 0.6
                    │
    ───────────────┼───────────────►
    0              │               1
    │              │               │
    │   LEGITIMATE │   PHISHING    │
    │              │               │
    │ ◆ ◆ ◆ ◆ ◆ ◆  │  ▲ ▲ ▲ ▲ ▲   │
    │              │               │

    ◆ = Email hợp lệ (mong muốn < 0.6)
    ▲ = Email phishing (mong muốn >= 0.6)
```

---

## 7. Ensemble Score - Điểm tổng hợp

### 7.1 Tại sao cần Ensemble Score?

Model probability đôi khi không đủ. Ta kết hợp thêm các yếu tố:

```
Model probability: 0.55 (sát ngưỡng)
Nhưng email có:
  - 5 links đến domain lạ
  - Chứa từ "urgent", "suspended"

→ Nên tăng điểm rủi ro!
```

### 7.2 Công thức Ensemble Score

```python
# File: src/features.py (lines 232-292)

ensemble_score = (
    model_proba * 0.60 +       # Model prediction: 60%
    urgent_risk * 0.15 +       # Urgent keywords: 15%
    links_risk * 0.15 +        # Links risk: 15%
    sender_risk * 0.10         # Sender risk: 10%
)
```

### 7.3 Tính từng thành phần

#### Urgent Risk

```python
urgent_risk = 1.0 if có từ khóa khẩn cấp else 0.0
```

#### Links Risk

```python
if links_count == 0:
    links_risk = 0.0
elif links_count == 1:
    links_risk = 0.2
elif links_count <= 3:
    links_risk = 0.4
elif links_count <= 5:
    links_risk = 0.6
else:
    links_risk = 0.8
```

#### Sender Risk

```python
if sender_domain in TRUSTED_DOMAINS:
    sender_risk = 0.0           # Trusted
elif "suspicious patterns" in sender_domain:
    sender_risk = 0.8           # Suspicious
elif sender_domain ends with [".xyz", ".top", ".click"]:
    sender_risk = 0.6           # Risky TLD
else:
    sender_risk = 0.1           # Normal
```

### 7.4 Trusted Domain Bonus

```python
# Nếu sender domain trusted VÀ 80%+ links trusted:
ensemble_score *= 0.6          # Giảm 40%

# Nếu CHỈ sender domain trusted HOẶC links trusted:
ensemble_score *= 0.8          # Giảm 20%
```

### 7.5 Ví dụ tính toán

**Email phishing:**

```
Content: "URGENT! Verify your account at https://paypa1-secure.xyz immediately!"
Sender: support@paypa1-secure.xyz

Model probability: 0.75
Urgent keywords: Có (1)
Links count: 1
Sender domain: paypa1-secure.xyz (suspicious TLD)

Ensemble = 0.75 * 0.60 + 1.0 * 0.15 + 0.2 * 0.15 + 0.6 * 0.10
         = 0.45 + 0.15 + 0.03 + 0.06
         = 0.69

→ Phishing (>= 0.6)
```

**Email hợp lệ từ LinkedIn:**

```
Content: "You have 3 new connection requests"
Sender: notifications@linkedin.com

Model probability: 0.35
Urgent keywords: Không (0)
Links count: 2 (đến linkedin.com)
Sender domain: linkedin.com (trusted)

Ensemble = 0.35 * 0.60 + 0.0 * 0.15 + 0.1 * 0.15 + 0.0 * 0.10
         = 0.21 + 0 + 0.015 + 0
         = 0.225

Trusted bonus: 0.225 * 0.6 = 0.135

→ Legitimate (< 0.6)
```

---

## 8. Code Reference

### 8.1 Các file liên quan

| File                   | Mô tả                                         |
| ---------------------- | --------------------------------------------- |
| `src/features.py`      | Pipeline trích xuất features + Ensemble score |
| `src/text_cleaning.py` | Các hàm trích xuất từng feature               |
| `src/train.py`         | Training pipeline + Threshold optimization    |
| `src/config.py`        | Trusted domains list                          |

### 8.2 Xem chi tiết code

```bash
# Xem feature pipeline
cat src/features.py

# Xem text cleaning functions
cat src/text_cleaning.py
```

---

## Câu hỏi ôn tập

1. TF-IDF đánh giá tầm quan trọng của từ dựa trên những yếu tố nào?
2. Tại sao cần dùng N-gram (1,2) thay vì chỉ Unigram?
3. Threshold 0.6 được chọn dựa trên tiêu chí gì?
4. Ensemble Score khác gì so với Model Probability đơn thuần?
5. Tại sao cần "Trusted Domain Bonus"?

---

_Tài liệu được tạo cho nhóm đồ án_  
_Cập nhật: Tháng 1/2026_
