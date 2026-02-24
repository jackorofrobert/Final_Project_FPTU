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

**Tại sao quan trọng?**

- Email phishing thường có nhiều link dẫn đến trang giả mạo
- Email hợp lệ thường có 0-2 link

**Thang điểm rủi ro:**
| Số link | Mức độ rủi ro |
|---------|---------------|
| 0 | 0.0 (An toàn) |
| 1 | 0.2 (Thấp) |
| 2-3 | 0.4 (Trung bình) |
| 4-5 | 0.6 (Cao) |
| >5 | 0.8 (Rất cao) |

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

# Ví dụ:
text1 = "Verify your account immediately!"
detect_urgent_keywords(text1)  # Output: 1

text2 = "Meeting schedule for next week"
detect_urgent_keywords(text2)  # Output: 0
```

**Tại sao quan trọng?**

- Phishing tạo cảm giác cấp bách để người dùng không suy nghĩ kỹ
- "Your account will be suspended in 24 hours!" → Điển hình phishing

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

# Ví dụ:
text = "Please see the attached invoice.pdf"
detect_attachment_mention(text)  # Output: 1
```

**Tại sao quan trọng?**

- Phishing thường đính kèm file độc hại
- Đề cập .exe, .scr → Rất đáng ngờ

### 4.4 body_length - Độ dài nội dung

```python
def length_chars(text: str) -> int:
    """Trả về độ dài văn bản (số ký tự)"""
    return len(str(text))

# Ví dụ:
length_chars("Verify now!")  # Output: 11
```

**Tại sao quan trọng?**

- Email phishing thường ngắn gọn, đi thẳng vào "call to action"
- Email newsletter/marketing thường dài hơn

### 4.5 exclamation_count - Số dấu chấm than

```python
def exclamation_count(text: str) -> int:
    """Đếm số dấu chấm than"""
    return str(text).count('!')

# Ví dụ:
text = "URGENT!!! Act NOW!!"
exclamation_count(text)  # Output: 5
```

**Tại sao quan trọng?**

- Phishing thường dùng nhiều dấu ! để tạo cảm giác cấp bách
- Email chuyên nghiệp hiếm khi có nhiều hơn 1-2 dấu !

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
