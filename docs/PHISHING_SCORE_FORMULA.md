# Công Thức Tính Điểm Phishing (Ensemble Score)

## Tổng quan

Hệ thống sử dụng **Ensemble Score** - kết hợp nhiều yếu tố để đưa ra kết quả chính xác hơn so với chỉ dùng model AI đơn thuần.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENSEMBLE SCORE (0% - 100%)                    │
├─────────────────────────────────────────────────────────────────┤
│  = Model Probability × 70%                                       │
│  + Urgent Keywords   × 12%                                       │
│  + Links Risk        × 10.5%                                     │
│  + Sender Risk       × 7.5%                                      │
│    ────────────────────────                                      │
│                       = 100%                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Chi tiết từng thành phần

### 1. Model Probability (70%)

Đây là xác suất từ model XGBoost - đã được train trên hàng ngàn email.

**Cách hoạt động:**

- Model phân tích **nội dung text** của email bằng TF-IDF (Term Frequency - Inverse Document Frequency)
- Kết hợp với các **features số** như số links, attachment, keywords
- Trả về xác suất từ 0.0 đến 1.0

**Ví dụ:**

```
Model trả về: 0.85 (85%)
Đóng góp = 0.85 × 0.70 = 0.595 (59.5%)
```

**Code tham khảo:** [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L338-L394)

---

### 2. Urgent Keywords (12%)

Phát hiện các từ khóa "khẩn cấp" thường xuất hiện trong email phishing.

**Danh sách từ khóa (trong `text_cleaning.py`):**

| Nhóm        | Từ khóa                                                              |
| ----------- | -------------------------------------------------------------------- |
| Khẩn cấp    | `urgent`, `act now`, `immediate`, `expires`, `limited time`          |
| Tài khoản   | `account suspended`, `verify now`, `confirm your`, `action required` |
| Bảo mật     | `security alert`, `unusual activity`, `password expired`             |
| Phần thưởng | `winner`, `congratulations`, `free gift`                             |

**Cách tính:**

- Có từ khóa → `urgent_keywords = 1`
- Không có → `urgent_keywords = 0`

**Ví dụ:**

```
Email: "Verify now your account immediately!"
→ urgent_keywords = 1
→ Đóng góp = 1 × 0.12 = 0.12 (12%)
```

---

### 3. Links Risk (10.5%)

Phân tích các link trong email và đánh giá độ nguy hiểm.

**Bảng phân loại link:**

| Loại link      | Risk Score | Mô tả                  | Ví dụ                                |
| -------------- | ---------- | ---------------------- | ------------------------------------ |
| **IP_BASED**   | 90%        | Dùng IP thay vì domain | `http://192.168.1.1/login`           |
| **SUSPICIOUS** | 70-80%     | Chứa pattern đáng ngờ  | URL có "login", "verify", "password" |
| **SHORTENER**  | 60%        | URL rút gọn            | `bit.ly`, `tinyurl.com`, `t.co`      |
| **NORMAL**     | 10%        | Link bình thường       | `example.com/page`                   |
| **TRUSTED**    | 0%         | Domain trong whitelist | Domain bạn tự thêm                   |

**Công thức:**

```
Links Risk = Trung bình risk của tất cả links trong email
```

**Ví dụ:**

```
Email có 2 links:
  - bit.ly/xxx → risk = 0.6 (shortener)
  - 192.168.1.1/login → risk = 0.9 (IP-based)

Links Risk = (0.6 + 0.9) / 2 = 0.75
Đóng góp = 0.75 × 0.105 = 0.079 (7.9%)
```

**Fallback (khi không extract được domain):**

| Số links | Risk |
| -------- | ---- |
| 0        | 0%   |
| 1        | 15%  |
| 2-3      | 25%  |
| 4-5      | 40%  |
| >5       | 60%  |

**Code tham khảo:** [features.py - calculate_links_risk()](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L286-L335)

---

### 4. Sender Risk (7.5%)

Đánh giá độ tin cậy của domain người gửi email.

**Logic:**

```
                    ┌──────────────────────┐
                    │   Sender Domain      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Trong TRUSTED_DOMAINS?│
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
        ┌─────▼─────┐                     ┌─────▼─────┐
        │    CÓ     │                     │   KHÔNG   │
        │ Risk = 0% │                     │ Risk = 50%│
        │ TRUSTED   │                     │SUSPICIOUS │
        └───────────┘                     └───────────┘
```

**Cách cấu hình whitelist (trong `config.py`):**

```python
TRUSTED_DOMAINS = [
    'company.com',      # Công ty của bạn
    'partner.vn',       # Đối tác
    'gmail.com',        # Email cá nhân tin cậy
]
```

**Ví dụ:**

```
Sender: info@company.com (trong whitelist)
→ Sender Risk = 0%
→ Đóng góp = 0 × 0.075 = 0

Sender: hacker@unknown.xyz (không trong whitelist)
→ Sender Risk = 50%
→ Đóng góp = 0.5 × 0.075 = 0.0375 (3.75%)
```

**Code tham khảo:** [features.py - classify_domain()](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L182-L208)

---

## Code Tính Toán Công Thức

### Luồng gọi hàm (Call Flow)

```
predict.py                          features.py                    text_cleaning.py
──────────                          ───────────                    ────────────────

main()
  │
  ├─ extract_features_from_text()
  │    ├─ normalize_text()         ◄─────────────────────────────── text_cleaning.py:L16
  │    ├─ count_urls()             ◄─────────────────────────────── text_cleaning.py:L34
  │    ├─ detect_urgent_keywords() ◄─────────────────────────────── text_cleaning.py:L48
  │    ├─ extract_sender_domain()  ◄─────────────────────────────── text_cleaning.py:L61
  │    └─ prepare_features()       ◄── features.py:L89
  │
  ├─ model.predict_proba(X)        ← XGBoost trả về xác suất (0.0 - 1.0)
  │
  ├─ extract_link_domains()        ◄─────────────────────────────── text_cleaning.py:L75
  │
  └─ calculate_ensemble_score()    ◄── features.py:L338
       ├─ float(urgent_keywords)        → urgent_risk    (0 hoặc 1)
       ├─ calculate_links_risk()        → links_risk     (0.0 - 1.0)
       │    └─ classify_link()          ◄── features.py:L211
       ├─ classify_domain()             → domain_risk    (0.0 hoặc 0.5)
       │    └─ is_trusted_domain()      ◄── features.py:L154
       │
       └─ ensemble_score = Σ (risk × weight)
```

### Bước 1: Trích xuất Features từ email

**File:** [predict.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/predict.py#L31-L73) → `extract_features_from_text()`

```python
# predict.py dòng 31-73
def extract_features_from_text(raw_text, ...):
    normalized_text = normalize_text(raw_text)       # Loại HTML, chuẩn hóa text
    links_count = count_urls(raw_text)               # Đếm số URL bằng regex
    urgent_keywords = detect_urgent_keywords(raw_text)  # Có từ khóa khẩn cấp? (0/1)
    sender_domain = extract_sender_domain(raw_text)  # Extract domain từ "From: xxx@domain.com"

    return prepare_features(text=normalized_text, ...)  # → DataFrame cho model
```

### Bước 2: Model XGBoost trả về xác suất

**File:** [predict.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/predict.py#L233-L234)

```python
# predict.py dòng 234
proba_phishing = float(model.predict_proba(X)[0][1])
# model.predict_proba(X) trả về: [[prob_hợp_lệ, prob_lừa_đảo]]
# Ví dụ: [[0.15, 0.85]] → lấy 0.85 (85% là lừa đảo)
```

### Bước 3: Tính Ensemble Score (hàm chính)

**File:** [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L338-L447) → `calculate_ensemble_score()`

```python
# features.py dòng 338-447
def calculate_ensemble_score(model_proba, urgent_keywords, links_count,
                              sender_domain, has_attachment, link_domains, urls):

    # ── Bước 3a: Tính risk từng thành phần ──
    urgent_risk = float(urgent_keywords)       # Dòng 370: Chuyển 0/1 thành float
    links_risk = calculate_links_risk(...)     # Dòng 371: Gọi hàm tính risk links
    _, domain_risk, _ = classify_domain(...)   # Dòng 372: Gọi hàm phân loại sender

    # ── Bước 3b: Khai báo trọng số ──
    W_MODEL  = 0.70    # Dòng 396
    W_URGENT = 0.12    # Dòng 397
    W_LINKS  = 0.105   # Dòng 398
    W_DOMAIN = 0.075   # Dòng 399

    # ── Bước 3c: Tính đóng góp từng thành phần ──
    model_contrib  = model_proba * W_MODEL     # Dòng 402
    urgent_contrib = urgent_risk * W_URGENT    # Dòng 403
    links_contrib  = links_risk  * W_LINKS     # Dòng 404
    domain_contrib = domain_risk * W_DOMAIN    # Dòng 405

    # ── Bước 3d: Tổng hợp ──
    ensemble_score = model_contrib + urgent_contrib + links_contrib + domain_contrib  # Dòng 407
    ensemble_score = max(0.0, min(1.0, ensemble_score))  # Dòng 408: Giới hạn 0-1
```

### Bước 3a chi tiết: Hàm `classify_domain()` — Sender Risk

**File:** [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L182-L208)

```python
# features.py dòng 182-208
def classify_domain(domain):
    from .config import TRUSTED_DOMAINS  # Lấy whitelist từ config.py

    if not domain or domain == "unknown":
        return ("SUSPICIOUS", 0.5, "Domain không xác định")

    if is_trusted_domain(domain, TRUSTED_DOMAINS):  # So sánh với whitelist
        return ("TRUSTED", 0.0, "Domain trong whitelist của bạn")

    return ("SUSPICIOUS", 0.5, "Domain không trong whitelist")
```

**File:** [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L154-L179) → `is_trusted_domain()`

```python
# features.py dòng 154-179
def is_trusted_domain(domain, trusted_list):
    domain_lower = domain.lower()
    for trusted in trusted_list:
        if domain_lower == trusted or domain_lower.endswith('.' + trusted):
            return True  # "mail.company.com" khớp với "company.com"
    return False
```

### Bước 3a chi tiết: Hàm `calculate_links_risk()` — Links Risk

**File:** [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L286-L335)

```python
# features.py dòng 286-335
def calculate_links_risk(links_count, link_domains, urls):
    if links_count == 0:
        return 0.0                         # Không có link → risk = 0

    # Ưu tiên 1: Nếu có đầy đủ URLs → phân loại từng link
    if urls:
        total_risk = 0.0
        for url in urls:
            _, risk, _ = classify_link(url)  # Gọi hàm phân loại link
            total_risk += risk
        return total_risk / len(urls)        # Trung bình risk

    # Ưu tiên 2: Chỉ có domain → kiểm tra trusted/shortener
    if link_domains:
        # ... tính risk dựa trên domain

    # Fallback: Chỉ có số lượng link
    # 1 link → 0.15, 2-3 → 0.25, 4-5 → 0.4, >5 → 0.6
```

### Bước 3a chi tiết: Hàm `classify_link()` — Phân loại từng link

**File:** [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py#L211-L267)

```python
# features.py dòng 211-267
def classify_link(url):
    # 1. Kiểm tra IP_BASED (nguy hiểm nhất)
    if re.search(r'https?://\d+\.\d+\.\d+\.\d+', url):
        return ("IP_BASED", 0.9, "Dùng IP thay vì domain")

    # 2. Kiểm tra SHORTENER (URL rút gọn)
    for shortener in SHORTENER_DOMAINS:    # bit.ly, tinyurl.com, t.co...
        if domain == shortener:
            return ("SHORTENER", 0.6, f"URL rút gọn ({shortener})")

    # 3. Kiểm tra TRUSTED (domain trong whitelist)
    if is_trusted_domain(domain, TRUSTED_DOMAINS):
        return ("TRUSTED", 0.0, "Link đến domain trusted")

    # 4. Kiểm tra SUSPICIOUS patterns trong URL
    suspicious_patterns = [
        r'login|signin|verify|confirm',    # → 0.7
        r'password|credential|ssn|credit', # → 0.7
        r'\.exe|\.zip|\.rar|\.scr',        # → 0.7
    ]

    # 5. Mặc định: NORMAL
    return ("NORMAL", 0.1, "Link bình thường")
```

### Bước 4: Phân loại kết quả

**File:** [predict.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/predict.py#L253-L261)

```python
# predict.py dòng 253-261
if ensemble_score < threshold:                        # < 0.5
    classification = "LEGITIMATE"
elif ensemble_score < threshold + suspicious_margin:  # 0.5 - 0.7
    classification = "SUSPICIOUS"
else:                                                 # >= 0.7
    classification = "PHISHING"
```

### Nơi gọi hàm `calculate_ensemble_score()`

**File:** [predict.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/predict.py#L241-L248) (CLI)

```python
# predict.py dòng 241-248
ensemble_result = calculate_ensemble_score(
    model_proba=proba_phishing,           # Từ XGBoost
    urgent_keywords=int(X['urgent_keywords'].iloc[0]),
    links_count=int(X['links_count'].iloc[0]),
    sender_domain=X['sender_domain'].iloc[0],
    has_attachment=int(X['has_attachment'].iloc[0]),
    link_domains=link_domains             # Từ extract_link_domains()
)
```

**File:** [prediction_service.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/app/services/prediction_service.py) (API Server)

```python
# prediction_service.py — Luồng tương tự nhưng qua API endpoint
ensemble_result = calculate_ensemble_score(
    model_proba=proba_phishing,
    ...
)
# Trả về formula_details trong JSON response
```

---

## Phân loại kết quả (Classification)

Sau khi tính Ensemble Score, hệ thống phân loại thành 3 mức:

```
 0%        50%                70%                100%
  │         │                  │                  │
  ├─────────┼──────────────────┼──────────────────┤
  │ LEGITIMATE │   SUSPICIOUS    │    PHISHING     │
  │  (An toàn)  │   (Nghi ngờ)    │   (Lừa đảo)    │
  └─────────────┴────────────────┴─────────────────┘

  threshold = 0.5 (50%)
  suspicious_margin = 0.2 (20%)
```

| Điều kiện           | Phân loại  | Icon |
| ------------------- | ---------- | ---- |
| `score < 0.5`       | LEGITIMATE | ✅   |
| `0.5 ≤ score < 0.7` | SUSPICIOUS | ⚠️   |
| `score ≥ 0.7`       | PHISHING   | 🚨   |

**Các ngưỡng có thể điều chỉnh trong `config.py`:**

```python
DEFAULT_THRESHOLD = 0.5      # Ngưỡng phân biệt an toàn/nghi ngờ
SUSPICIOUS_MARGIN = 0.2      # Khoảng cách từ nghi ngờ đến phishing
```

---

## Ví dụ hoàn chỉnh

**Email đầu vào:**

```
From: support@unknownbank.xyz
Subject: Urgent! Verify your account

Dear Customer,
Your account has been temporarily suspended.
Please click here to verify: http://bit.ly/verify123

Immediate action required!
```

### Bước 1: Thu thập Features

| Feature         | Giá trị                         | Nguồn                                     |
| --------------- | ------------------------------- | ----------------------------------------- |
| text            | "urgent verify your account..." | Email content                             |
| urgent_keywords | 1                               | Phát hiện "urgent", "verify", "immediate" |
| links_count     | 1                               | Có 1 link bit.ly                          |
| link_domains    | ["bit.ly"]                      | Extract từ URL                            |
| sender_domain   | "unknownbank.xyz"               | Không trong whitelist                     |

### Bước 2: Model Prediction

```
XGBoost phân tích text và features
→ model_proba = 0.72 (72%)
```

### Bước 3: Tính Risk Scores

| Thành phần  | Giá trị | Lý do                                  |
| ----------- | ------- | -------------------------------------- |
| urgent_risk | 1.0     | Có từ khóa khẩn cấp                    |
| links_risk  | 0.6     | bit.ly là URL shortener                |
| sender_risk | 0.5     | Domain người gửi không trong whitelist |

### Bước 4: Tính Ensemble Score

```
Ensemble = model_proba × 0.70 + urgent_risk × 0.12 + links_risk × 0.105 + sender_risk × 0.075
         = 0.72 × 0.70       + 1.0 × 0.12        + 0.6 × 0.105        + 0.5 × 0.075
         = 0.504             + 0.12              + 0.063              + 0.0375
         = 0.7245 (72.45%)
```

### Bước 5: Phân loại

```
0.7245 ≥ 0.7 (threshold + margin)
→ 🚨 PHISHING
```

---

## Sơ đồ Luồng Xử lý

```
┌──────────────────────────────────────────────────────────────────────┐
│                          EMAIL ĐẦU VÀO                               │
│  "Urgent! Verify account at bit.ly/xxx"                              │
│  From: hacker@unknown.xyz                                            │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  XGBoost AI   │      │ Feature-Based │      │   Trust DB    │
│   (70%)       │      │   Analysis    │      │   Lookup      │
│               │      │               │      │               │
│ TF-IDF + ML   │      │ Keywords 12%  │      │ Sender → 0%   │
│ → probability │      │ Links   10.5% │      │ hoặc 50%      │
│               │      │ Sender   7.5% │      │               │
└───────┬───────┘      └───────┬───────┘      └───────┬───────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │       ENSEMBLE SCORE           │
              │  = Tổng trọng số các thành phần │
              └────────────────┬───────────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │      CLASSIFICATION            │
              │                                │
              │  < 50%  → ✅ LEGITIMATE        │
              │  50-70% → ⚠️ SUSPICIOUS        │
              │  ≥ 70%  → 🚨 PHISHING          │
              └────────────────────────────────┘
```

---

## Tại sao dùng Ensemble thay vì chỉ Model?

| Vấn đề với Model đơn                                  | Giải pháp Ensemble                            |
| ----------------------------------------------------- | --------------------------------------------- |
| Model có thể miss email phishing mới                  | Feature-based rules bắt được patterns cố định |
| Model có thể false positive email hợp lệ từ domain lạ | Trust DB cho phép whitelist domain tin cậy    |
| Không giải thích được tại sao email bị đánh dấu       | Score breakdown cho từng thành phần           |

---

## Files liên quan

| File                                                                                                        | Mô tả                                                                        |
| ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [features.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/features.py)                              | Công thức Ensemble Score + `calculate_ensemble_score()` trả về dict chi tiết |
| [predict.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/predict.py)                                | Module prediction CLI - hiển thị chi tiết formula                            |
| [config.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/config.py)                                  | Cấu hình threshold, trusted domains                                          |
| [text_cleaning.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/src/text_cleaning.py)                    | Extract features từ text                                                     |
| [prediction_service.py](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/app/services/prediction_service.py) | Service API - truyền `formula_details` vào response                          |
| [app.js](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/frontend/js/app.js)                                | Frontend - hiển thị bảng chi tiết formula                                    |

---

## Xem Chi Tiết Công Thức (Formula Details Output)

Hệ thống trả về chi tiết từng thành phần qua 3 kênh:

### CLI (Command Line)

```bash
python -m src.predict --text "Verify your account" --json
```

Kết quả JSON sẽ bao gồm field `formula_details`:

```json
{
  "formula_details": {
    "model": { "raw_score": 0.72, "weight": 0.70, "contribution": 0.504, "description": "..." },
    "urgent_keywords": { "raw_score": 1, "weight": 0.12, "contribution": 0.12, "description": "..." },
    "links": { "raw_score": 0.6, "weight": 0.105, "contribution": 0.063, "count": 1, "details": [...] },
    "domain": { "raw_score": 0.5, "weight": 0.075, "contribution": 0.0375, "domain_name": "...", "domain_type": "SUSPICIOUS", "reason": "..." },
    "formula_text": "Ensemble = 0.7200×70% + 1×12% + 0.6000×10.5% + 0.5000×7.5% = 0.7245"
  }
}
```

### API (REST)

`POST /api/v1/predictions/analyze` trả về `formula_details` trong response data.

> Xem chi tiết: [api.md](file:///c:/Users/LTT/Desktop/Final_Project_FPTU/docs/api.md)

### Web UI (Frontend)

Trang Analyze hiển thị bảng chi tiết:

| Thành phần                     | Raw Score | Weight | Contribution |
| ------------------------------ | --------- | ------ | ------------ |
| 🤖 Model Probability           | 72.00%    | 70%    | 50.40%       |
| 🚨 Urgent Keywords             | 1         | 12%    | 12.00%       |
| 🔗 Links Risk (1 link)         | 60.00%    | 10.5%  | 6.30%        |
| 🌐 Sender Risk → ⚠️ SUSPICIOUS | 50.00%    | 7.5%   | 3.75%        |
| **🎯 Ensemble Score**          |           |        | **72.45%**   |

Kèm theo:

- Badge domain: ✅ TRUSTED hoặc ⚠️ SUSPICIOUS + lý do
- Bảng phân loại từng link (URL, type, risk, reason)
- Công thức text dạng monospace
