# Hướng Dẫn Làm Sạch Dữ Liệu (Data Cleaning Guide)

> **📚 Tài liệu kỹ thuật** - Giải thích chi tiết quy trình chuyển đổi dữ liệu thô thành dataset sạch để huấn luyện mô hình.

---

## Mục Lục

1. [Tổng quan quy trình](#1-tổng-quan-quy-trình)
2. [Bước 1: Load dữ liệu thô](#2-bước-1-load-dữ-liệu-thô)
3. [Bước 2: Tiền xử lý Dataset](#3-bước-2-tiền-xử-lý-dataset)
4. [Bước 3: Làm sạch văn bản](#4-bước-3-làm-sạch-văn-bản)
5. [Bước 4: Chuẩn hóa nhãn](#5-bước-4-chuẩn-hóa-nhãn)
6. [Bước 5: Trích xuất Features](#6-bước-5-trích-xuất-features)
7. [Các file liên quan](#7-các-file-liên-quan)

---

## 1. Tổng quan quy trình

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    QUY TRÌNH LÀM SẠCH DỮ LIỆU                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Raw Data                                                              │
│   (Merged_Dataset_Clean.csv)                                            │
│            │                                                            │
│            ▼                                                            │
│   ┌─────────────────────┐                                               │
│   │ 1. Load & Encoding  │  ← Xử lý UTF-8/Latin1, delimiter              │
│   └──────────┬──────────┘                                               │
│              ▼                                                          │
│   ┌─────────────────────┐                                               │
│   │ 2. Tiền xử lý       │  ← Lọc label, xóa dòng lỗi                    │
│   └──────────┬──────────┘                                               │
│              ▼                                                          │
│   ┌─────────────────────┐                                               │
│   │ 3. Làm sạch văn bản │  ← Xóa HTML, chuẩn hóa khoảng trắng           │
│   └──────────┬──────────┘                                               │
│              ▼                                                          │
│   ┌─────────────────────┐                                               │
│   │ 4. Chuẩn hóa nhãn   │  ← Chuyển về 0/1                              │
│   └──────────┬──────────┘                                               │
│              ▼                                                          │
│   ┌─────────────────────┐                                               │
│   │ 5. Trích xuất       │  ← Tạo features từ nội dung                   │
│   │    Features         │                                               │
│   └──────────┬──────────┘                                               │
│              ▼                                                          │
│   Dataset_Ready.csv                                                     │
│   (212,085 rows, sẵn sàng train)                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Bước 1: Load dữ liệu thô

### 2.1 Code xử lý

```python
# File: src/data_io.py

def _safe_read_csv(path: Path) -> pd.DataFrame:
    """
    Robust CSV reader - xử lý các file CSV messy từ Windows/Excel
    """
    try:
        # Thử đọc với UTF-8 trước
        return pd.read_csv(
            path, 
            encoding="utf-8", 
            sep=None,              # Auto-detect delimiter
            engine="python", 
            on_bad_lines="skip"    # Bỏ qua dòng lỗi
        )
    except UnicodeDecodeError:
        # Fallback sang Latin1 nếu UTF-8 fail
        return pd.read_csv(
            path, 
            encoding="latin1", 
            sep=None, 
            engine="python", 
            on_bad_lines="skip"
        )
```

### 2.2 Các vấn đề thường gặp và cách xử lý

| Vấn đề | Nguyên nhân | Cách xử lý |
|--------|-------------|------------|
| `UnicodeDecodeError` | File không phải UTF-8 | Fallback sang Latin1 |
| Dòng bị lỗi parsing | Dữ liệu chứa ký tự đặc biệt | `on_bad_lines='skip'` |
| Delimiter sai | File dùng `;` thay vì `,` | `sep=None` auto-detect |
| Multiline content | Body email có nhiều dòng | `quoting=1` (QUOTE_ALL) |

### 2.3 Hỗ trợ nhiều định dạng

```python
# File: src/data_io.py

def load_any(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    
    if suffix in [".csv", ".tsv", ".txt"]:
        return _safe_read_csv(path)
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    if suffix in [".json"]:
        return pd.read_json(path, lines=True)
```

---

## 3. Bước 2: Tiền xử lý Dataset

### 3.1 Script chuẩn bị

```python
# File: scripts/prepare_dataset.py

import pandas as pd

# 1. Load với xử lý quoting cho nội dung multiline
df = pd.read_csv(
    'data/incoming/Merged_Dataset_Clean.csv',
    quoting=1,              # QUOTE_ALL - xử lý nội dung có dấu ngoặc kép
    on_bad_lines='skip',    # Bỏ qua dòng lỗi
    engine='python'
)

print(f"Loaded rows: {len(df):,}")  # Ví dụ: 250,000 rows
```

### 3.2 Lọc dữ liệu hợp lệ

```python
# 2. Chuyển label sang numeric
df['label'] = pd.to_numeric(df['label'], errors='coerce')

# 3. Lọc chỉ giữ label hợp lệ (0 hoặc 1)
df_clean = df[df['label'].isin([0.0, 1.0])].copy()

# 4. Xóa dòng thiếu body hoặc label
df_clean = df_clean.dropna(subset=['body', 'label'])

# 5. Xóa dòng body quá ngắn (< 10 ký tự = nhiễu)
df_clean = df_clean[df_clean['body'].str.len() > 10]
```

### 3.3 Kết quả sau tiền xử lý

| Chỉ số | Trước | Sau | Ghi chú |
|--------|-------|-----|---------|
| Tổng số dòng | ~250,000 | 212,085 | Giảm ~15% |
| Label = 0 (Hợp lệ) | - | 113,096 | 53.3% |
| Label = 1 (Phishing) | - | 98,989 | 46.7% |
| Dòng bị xóa | - | ~38,000 | Label NaN, body ngắn |

### 3.4 Lưu file sạch

```python
# 6. Lưu thành Dataset_Ready.csv
output_path = 'data/incoming/Dataset_Ready.csv'
df_clean.to_csv(output_path, index=False, quoting=1)
```

---

## 4. Bước 3: Làm sạch văn bản

### 4.1 Loại bỏ HTML tags

```python
# File: src/text_cleaning.py

from bs4 import BeautifulSoup

def strip_html(text: str) -> str:
    """Loại bỏ tất cả HTML tags, giữ lại nội dung text"""
    if text is None:
        return ""
    
    s = str(text)
    
    # Chỉ parse nếu có dấu hiệu HTML
    if "<" in s and ">" in s:
        try:
            return BeautifulSoup(s, "html.parser").get_text(separator=" ")
        except Exception:
            return s
    return s
```

**Ví dụ:**
```
Input:  "<html><body><p>Click <a href='link'>here</a></p></body></html>"
Output: "Click here"
```

### 4.2 Chuẩn hóa văn bản

```python
import re

_whitespace_re = re.compile(r"\s+")

def normalize_text(text: str) -> str:
    """Chuẩn hóa khoảng trắng và ký tự đặc biệt"""
    s = strip_html(text)
    
    # Xóa null character
    s = s.replace("\x00", " ")
    
    # Chuẩn hóa khoảng trắng (nhiều space → 1 space)
    s = _whitespace_re.sub(" ", s)
    
    return s.strip()
```

**Ví dụ:**
```
Input:  "Hello    world\n\n\tClick   here"
Output: "Hello world Click here"
```

---

## 5. Bước 4: Chuẩn hóa nhãn

### 5.1 Mapping các format nhãn

```python
# File: src/data_io.py

def coerce_label(y: pd.Series) -> pd.Series:
    """Chuyển đổi các format nhãn khác nhau về 0/1"""
    
    mapping = {
        # Phishing = 1
        "1": 1,
        "phishing": 1,
        "spam": 1,
        "malicious": 1,
        "fraud": 1,
        
        # Legitimate = 0
        "0": 0,
        "benign": 0,
        "legit": 0,
        "legitimate": 0,
        "ham": 0,
        "normal": 0
    }
    
    y2 = y.astype(str).str.strip().str.lower()
    y2 = y2.map(lambda v: mapping.get(v, v))
    return y2.astype(int)
```

### 5.2 Các format được hỗ trợ

| Format gốc | Chuyển thành |
|------------|--------------|
| `1`, `"1"`, `1.0` | 1 (Phishing) |
| `"phishing"`, `"spam"`, `"malicious"` | 1 (Phishing) |
| `0`, `"0"`, `0.0` | 0 (Legitimate) |
| `"legitimate"`, `"benign"`, `"ham"` | 0 (Legitimate) |

---

## 6. Bước 5: Trích xuất Features

### 6.1 Tự động trích xuất từ body

```python
# File: src/train.py - function ensure_feature_columns()

from .text_cleaning import (
    count_urls, detect_urgent_keywords, extract_sender_domain,
    detect_attachment_mention, exclamation_count, length_chars
)

def ensure_feature_columns(df, text_col='body'):
    text_content = df[text_col].astype(str)
    
    # Đếm số URL
    if 'links_count' not in df.columns:
        df['links_count'] = text_content.apply(count_urls)
    
    # Phát hiện từ khóa khẩn cấp
    if 'urgent_keywords' not in df.columns:
        df['urgent_keywords'] = text_content.apply(detect_urgent_keywords)
    
    # Phát hiện đề cập file đính kèm
    if 'has_attachment' not in df.columns:
        df['has_attachment'] = text_content.apply(detect_attachment_mention)
    
    # Trích xuất domain người gửi
    if 'sender_domain' not in df.columns:
        df['sender_domain'] = text_content.apply(extract_sender_domain)
    
    # Độ dài nội dung
    if 'body_length' not in df.columns:
        df['body_length'] = text_content.apply(length_chars)
    
    # Số dấu chấm than
    if 'exclamation_count' not in df.columns:
        df['exclamation_count'] = text_content.apply(exclamation_count)
    
    return df
```

### 6.2 Chi tiết các hàm trích xuất

#### A. count_urls - Đếm số URL

```python
import re
_url_re = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)

def count_urls(text: str) -> int:
    """Đếm số lượng URL trong văn bản"""
    if text is None:
        return 0
    return len(_url_re.findall(str(text)))

# Ví dụ:
# "Visit https://google.com and www.facebook.com" → 2
```

#### B. detect_urgent_keywords - Phát hiện từ khóa khẩn cấp

```python
URGENT_KEYWORDS = [
    'urgent', 'immediately', 'action required', 'act now', 'suspend',
    'verify', 'confirm', 'expire', 'limited time', 'final notice',
    'warning', 'alert', 'security', 'locked', 'disabled', 'blocked',
    'unauthorized', 'suspicious', 'unusual', 'violation', 'risk',
    '24 hours', '48 hours', 'deadline', 'asap', 'important'
]

def detect_urgent_keywords(text: str) -> int:
    """Trả về 1 nếu có từ khóa khẩn cấp, 0 nếu không"""
    text_lower = str(text).lower()
    for keyword in URGENT_KEYWORDS:
        if keyword in text_lower:
            return 1
    return 0

# Ví dụ:
# "Verify your account immediately!" → 1
# "Meeting schedule for next week" → 0
```

#### C. detect_attachment_mention - Phát hiện đề cập file đính kèm

```python
ATTACHMENT_KEYWORDS = [
    'attached', 'attachment', 'attachments', 'see attached',
    'enclosed', 'find attached', 'please find', 'attached file',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.exe', '.jpg', '.png', '.gif'
]

def detect_attachment_mention(text: str) -> int:
    """Trả về 1 nếu đề cập attachment, 0 nếu không"""
    text_lower = str(text).lower()
    for keyword in ATTACHMENT_KEYWORDS:
        if keyword in text_lower:
            return 1
    return 0
```

#### D. extract_sender_domain - Trích xuất domain

```python
_email_re = re.compile(r"[\w\.-]+@([\w\.-]+\.\w+)", re.IGNORECASE)

def extract_sender_domain(text: str) -> str:
    """Trích xuất domain từ địa chỉ email trong văn bản"""
    if text is None:
        return "unknown"
    
    matches = _email_re.findall(str(text))
    if matches:
        return matches[0].lower()
    
    return "unknown"

# Ví dụ:
# "From: support@paypal.com" → "paypal.com"
# "Contact admin@company.vn" → "company.vn"
```

---

## 7. Các file liên quan

| File | Mô tả | Chức năng |
|------|-------|-----------|
| `src/data_io.py` | Load và xử lý file | `load_any()`, `_safe_read_csv()` |
| `src/text_cleaning.py` | Làm sạch văn bản | `strip_html()`, `normalize_text()`, các hàm trích xuất |
| `src/label_utils.py` | Chuẩn hóa nhãn | `normalize_label()` |
| `src/train.py` | Training pipeline | `ensure_feature_columns()` |
| `scripts/prepare_dataset.py` | Script chuẩn bị data | Chạy một lần để tạo Dataset_Ready.csv |

---

## Hướng dẫn sử dụng

### Chạy script chuẩn bị dataset

```bash
cd c:\Users\LTT\Desktop\Final_Project_FPTU
python scripts/prepare_dataset.py
```

### Kiểm tra dataset sau khi làm sạch

```bash
python scripts/view_dataset.py
```

---

*Tài liệu được tạo cho nhóm đồ án*  
*Cập nhật: Tháng 1/2026*
