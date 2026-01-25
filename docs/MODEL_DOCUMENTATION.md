# Phishing Detection Model Documentation

## Tổng quan

Hệ thống phát hiện email phishing sử dụng Machine Learning kết hợp với phân tích features để đạt độ chính xác cao.

---

## 1. Kiến trúc Model

### 1.1 Multi-Feature Pipeline

```
Email Input
    │
    ├── Text Features ────────→ TF-IDF Vectorizer (5000 features)
    │                                    │
    ├── has_attachment ───────→ StandardScaler ──┐
    ├── links_count ──────────→               │  │
    ├── urgent_keywords ──────→               │  ├──→ ColumnTransformer ──→ XGBoost
    │                                         │  │
    └── sender_domain ────────→ OneHotEncoder ──┘
```

### 1.2 Ensemble Score

Kết hợp model probability với feature-based risk scores:

| Component | Weight | Mô tả |
|-----------|--------|-------|
| Model Probability | 60% | Dự đoán từ XGBoost |
| Urgent Keywords | 15% | Từ khóa khẩn cấp |
| Links Risk | 15% | Rủi ro từ số lượng links |
| Domain Risk | 10% | Rủi ro từ sender domain |

**Công thức:**
```
ensemble_score = model_prob × 0.6 + urgent × 0.15 + links_risk × 0.15 + domain_risk × 0.10
```

---

## 2. Features

### 2.1 Text Feature (TF-IDF)
- **Max features**: 5000
- **N-gram range**: (1, 2) - unigram và bigram
- **Stop words**: English removed

### 2.2 Numeric Features

| Feature | Kiểu | Mô tả |
|---------|------|-------|
| `has_attachment` | 0/1 | Email có đính kèm file |
| `links_count` | int | Số lượng links trong email |
| `urgent_keywords` | 0/1 | Chứa từ khóa khẩn cấp |

### 2.3 Categorical Feature

| Feature | Kiểu | Mô tả |
|---------|------|-------|
| `sender_domain` | string | Domain của người gửi (ví dụ: gmail.com) |

### 2.4 Urgent Keywords List

```python
URGENT_KEYWORDS = [
    'urgent', 'immediately', 'action required', 'act now', 'suspend',
    'verify', 'confirm', 'expire', 'limited time', 'final notice',
    'warning', 'alert', 'security', 'locked', 'disabled', 'blocked',
    'unauthorized', 'suspicious', 'unusual', 'violation', 'risk',
    '24 hours', '48 hours', 'deadline', 'asap', 'important'
]
```

---

## 3. Optimal Threshold

### 3.1 Cách tính

Threshold được tối ưu hóa dựa trên **F1-score** trên test set:

```python
for threshold in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7]:
    f1 = f1_score(y_test, y_pred >= threshold)
    if f1 > best_f1:
        best_threshold = threshold
```

### 3.2 Khi nào thay đổi?

| Trigger | Threshold thay đổi? |
|---------|---------------------|
| Prediction | ❌ Không |
| Retrain model | ✅ Có |
| Thêm data mới | ✅ Có (sau khi retrain) |

### 3.3 Ý nghĩa F1-score

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

- **Precision**: % phishing đúng trong tổng số báo phishing
- **Recall**: % phishing bắt được trong tổng số phishing thật

---

## 4. Risk Scoring

### 4.1 Domain Risk

| Domain Pattern | Risk Score |
|----------------|------------|
| Suspicious patterns (secure-, login-, verify-) | 0.8 (High) |
| Suspicious TLDs (.xyz, .click, .link) | 0.6 (Medium) |
| Unknown domain | 0.3 (Low-Medium) |
| Normal domain | 0.1 (Low) |

### 4.2 Links Risk

| Links Count | Risk Score |
|-------------|------------|
| 0 | 0.0 |
| 1 | 0.2 |
| 2-3 | 0.4 |
| 4-5 | 0.6 |
| 6+ | 0.8 |

---

## 5. Sử dụng

### 5.1 Training

```bash
python -m src.train --data-dir data --text-col email_text --label-col label --out models
```

**Output:**
- `models/model.joblib` - Trained model
- `models/metadata.json` - Training metadata

### 5.2 Prediction (CLI)

```bash
# Từ file
python -m src.predict --file samples/test.txt

# Từ text
python -m src.predict --text "Your account is suspended..."

# JSON output
python -m src.predict --file samples/test.txt --json
```

### 5.3 Prediction (API)

```bash
curl -X POST http://localhost:8000/api/v1/predictions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "Your account is suspended. Verify now!",
    "subject": "Urgent Security Alert",
    "links_count": 2,
    "urgent_keywords": 1
  }'
```

**Response:**
```json
{
  "prediction": 1,
  "probability": 0.85,
  "ensemble_score": 0.92,
  "threshold": 0.3,
  "is_phishing": true,
  "features": {
    "links_count": 2,
    "has_attachment": 0,
    "urgent_keywords": 1,
    "sender_domain": "unknown"
  }
}
```

---

## 6. Output Format

### 6.1 CLI Output

```
============================================================
 Email Classification Result
------------------------------------------------------------
Prediction     : PHISHING
Model Prob     : 100.00 %
Ensemble Score : 90.00 %
Threshold      : 0.3
------------------------------------------------------------
Extracted Features:
  - Links count    : 13
  - Has attachment : 0
  - Urgent keywords: 1
  - Sender domain  : unknown
------------------------------------------------------------
Suspicious Text Segments:
------------------------------------------------------------

[1] 🔴 HIGH - Score: 60%
    Text: "Your account will be suspended in 24 hours"
    Reasons: Từ khóa khẩn cấp: suspended, 24 hours

[2] 🟠 MEDIUM - Score: 40%
    Text: "Click here to verify your account"
    Reasons: Yêu cầu click, Yêu cầu xác minh
============================================================
```

### 6.2 Risk Levels

| Level | Score | Icon |
|-------|-------|------|
| HIGH | ≥ 60% | 🔴 |
| MEDIUM | 30-59% | 🟠 |
| LOW | < 30% | 🟡 |

---

## 7. File Structure

```
src/
├── train.py          # Training module
├── predict.py        # Prediction module
├── features.py       # Feature pipeline & ensemble score
├── text_cleaning.py  # Text preprocessing & keyword detection
├── label_utils.py    # Label normalization
└── data_io.py        # Data loading utilities

models/
├── model.joblib      # Trained model
└── metadata.json     # Training metadata

data/
├── incoming/         # New datasets (CSV/Excel)
└── history/          # Cached training datasets
```
