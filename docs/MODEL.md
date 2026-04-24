# Tài liệu Machine Learning Model — PhishGuard

Tài liệu mô tả pipeline Machine Learning cho hệ thống phát hiện email lừa đảo: từ dữ liệu thô đến huấn luyện, đánh giá và triển khai. Toàn bộ mã nguồn nằm trong thư mục [src/](../src/); model đã train được lưu trong [models/](../models/).

---

## 1. Tổng quan

| Thuộc tính | Giá trị |
|------------|--------|
| Bài toán | Phân loại nhị phân (phishing vs legitimate) |
| Thuật toán chính | XGBoost Classifier |
| Pipeline | `Pipeline(ColumnTransformer → XGBClassifier)` |
| Đặc trưng đầu vào | 7 (1 text TF-IDF + 5 số + 1 categorical) |
| Dataset huấn luyện | 410 674 email (48.3 % phishing / 51.7 % legitimate) |
| F1 tối ưu trên test | 0.9577 |
| Threshold tối ưu | 0.6 |
| Đầu ra | Phân loại 3 mức: `LEGITIMATE` / `SUSPICIOUS` / `PHISHING` |
| Định dạng model | `joblib` (`models/model.joblib`) |

### 1.1 Cấu trúc thư mục

```
src/
├── __init__.py
├── config.py           # Hằng số toàn cục: TRUSTED_DOMAINS, URL_SHORTENERS, URGENT_KEYWORDS
├── data_io.py          # Đọc dataset đa định dạng (csv/tsv/excel/json) + chuẩn hoá
├── text_cleaning.py    # Normalize text + trích xuất đặc trưng cơ bản
├── features.py         # Xây dựng pipeline ColumnTransformer + XGBoost
├── label_utils.py      # Chuẩn hoá nhãn về {0, 1}
├── train.py            # Entry point huấn luyện
└── predict.py          # Entry point dự đoán

models/
├── model.joblib                 # Pipeline đã train + metadata
├── metadata.json                # Threshold, F1, phân phối nhãn
├── logistic_regression.joblib   # Baseline (so sánh)
├── random_forest.joblib         # Baseline (so sánh)
└── xgboost.joblib               # Baseline XGBoost đơn lẻ
```

### 1.2 Sơ đồ pipeline

```
Raw email  →  Text cleaning  →  Feature extraction  →  TF-IDF + OneHot + Scaler
                                                          │
                                                          ▼
                                                    XGBoost
                                                          │
                                                          ▼
                                 Ensemble score (model + feature-based risk)
                                                          │
                                                          ▼
                                         LEGITIMATE / SUSPICIOUS / PHISHING
```

---

## 2. Dữ liệu

### 2.1 Nguồn dữ liệu

- `data/incoming/Merged_Dataset.csv` — dataset hợp nhất đa nguồn (chiếm 70 %).
- `data/incoming/Balanced_Dataset.csv` — dataset cân bằng nhân tạo (chiếm 30 %).
- `data/history/` — cache các file đã xử lý (đặt tên theo hash để tránh huấn luyện lại trùng).

### 2.2 `data_io.py`

Hỗ trợ đầu vào đa định dạng:

```python
load_any(path)              # Tự nhận CSV / TSV / Excel / JSON
                            # Phát hiện encoding (UTF-8, Latin-1)
                            # Phát hiện delimiter (',', ';', '\t', '|')
                            # Bỏ qua dòng hỏng

normalize_columns(df)       # Lowercase toàn bộ tên cột
auto_detect_columns(df, text_col, label_col)
                            # Tìm cột text/label theo heuristic
coerce_label(y)             # Chuẩn hoá nhãn về {0, 1}
```

### 2.3 Phân phối nhãn

Được ghi lại trong `models/metadata.json`:

```json
{
  "label_distribution": { "0.0": 212284, "1.0": 198390 },
  "n_phishing": 198390,
  "n_legit": 212284,
  "scale_pos_weight": 1.07
}
```

---

## 3. Tiền xử lý văn bản

Nằm trong [src/text_cleaning.py](../src/text_cleaning.py). Các bước chính:

### 3.1 `normalize_text(text)`

```python
def normalize_text(text: str) -> str:
    s = strip_html(text)              # BeautifulSoup gỡ tag HTML
    s = s.replace("\x00", " ")        # Loại null byte
    s = re.sub(r"\s+", " ", s).strip()# Gộp whitespace
    return s
```

### 3.2 Các hàm trích xuất phụ trợ

| Hàm | Mục đích |
|-----|---------|
| `count_urls(text)` | Đếm số URL (regex) |
| `exclamation_count(text)` | Đếm dấu chấm than |
| `detect_urgent_keywords(text)` | Kiểm tra ≥ 60 từ khoá khẩn cấp (0/1) |
| `extract_sender_domain(text)` | Lấy domain từ địa chỉ gửi |
| `extract_link_domains(text)` | Trả danh sách domain của toàn bộ URL |
| `detect_attachment_mention(text)` | Nhận diện đề cập tập tin đính kèm (0/1) |

### 3.3 Từ khoá khẩn cấp (mẫu)

```python
URGENT_KEYWORDS = [
    "urgent", "immediately", "action required", "verify", "confirm",
    "expire", "warning", "alert", "locked", "blocked", "unauthorized",
    "refund", "invoice", "payment", "password", "credential", "click here",
    "winner", "prize", "reward", "congratulations", ...
]
```

Danh sách đầy đủ nằm trong `src/config.py`.

---

## 4. Đặc trưng đầu vào

Model nhận 7 cột đầu vào (được định nghĩa trong `feature_cols` của `metadata.json`):

| Cột | Kiểu | Nguồn | Vai trò |
|-----|------|-------|--------|
| `text` | `str` (TF-IDF 5000 feature, n-gram 1–2) | Body email đã normalize | Nội dung từ vựng |
| `has_attachment` | `int` (0/1) | `detect_attachment_mention` | Có đính kèm hay không |
| `links_count` | `int` | `count_urls` | Số URL trong email |
| `urgent_keywords` | `int` (0/1) | `detect_urgent_keywords` | Có từ khoá khẩn cấp |
| `body_length` | `int` | `len(body)` | Độ dài email |
| `exclamation_count` | `int` | `exclamation_count` | Mức độ "kêu gọi" |
| `sender_domain` | `str` (OneHot) | `extract_sender_domain` | Domain người gửi |

Nếu dataset không có sẵn các cột số/categorical, `train.py` tự động trích xuất từ `text` trong bước tiền xử lý:

```python
if "has_attachment" not in df.columns:
    df["has_attachment"] = text_content.apply(detect_attachment_mention)
if "links_count" not in df.columns:
    df["links_count"] = text_content.apply(count_urls)
# ... tương tự cho các feature khác
```

---

## 5. Mô hình

### 5.1 Thuật toán và siêu tham số

```python
XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.7,
    min_child_weight=5,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.5,
    eval_metric="logloss",
    random_state=42,
)
```

### 5.2 Pipeline đầy đủ

```python
Pipeline([
    ("preprocessor", ColumnTransformer([
        ("text",        TfidfVectorizer(max_features=5000, ngram_range=(1, 2)), "text"),
        ("numeric",     StandardScaler(),                                       NUMERIC_COLS),
        ("categorical", OneHotEncoder(handle_unknown="ignore"),                 ["sender_domain"]),
    ])),
    ("clf", XGBClassifier(...)),
])
```

### 5.3 Chia tập và xử lý mất cân bằng

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42,
)

scale_pos_weight = n_legit / n_phishing   # ≈ 1.07
pipeline.set_params(clf__scale_pos_weight=scale_pos_weight)
```

### 5.4 Tìm ngưỡng tối ưu

Sau khi huấn luyện, `train.py` quét các giá trị threshold từ 0.3 đến 0.7 (step 0.05) và chọn giá trị tối đa hoá F1 trên tập test:

```python
best_threshold = 0.6
best_f1        = 0.9577
```

Kết quả được ghi vào `metadata.json` và dùng làm mặc định khi suy luận.

### 5.5 Các metric được báo cáo

- Accuracy, Precision, Recall, F1 (per class + macro).
- ROC-AUC, PR-AUC.
- Confusion matrix trên tập test.
- So sánh với baseline Logistic Regression và Random Forest (file `.joblib` cùng tên trong `models/`).

---

## 6. Ensemble scoring

Predict không chỉ dựa vào xác suất model — nó kết hợp với các tín hiệu hành vi để tăng tính giải thích và giảm nhầm lẫn:

```
Ensemble score =
      0.55 × Model probability
    + 0.20 × Urgent keyword risk
    + 0.15 × Links risk
    + 0.10 × Sender domain risk
```

### 6.1 Chi tiết từng thành phần

**Model probability (55 %)** — Output `predict_proba()[:, 1]` từ XGBoost.

**Urgent keyword risk (20 %)** — 1 nếu phát hiện keyword, 0 nếu không.

**Links risk (15 %)** — Trung bình điểm của các URL:

| Loại URL | Điểm |
|----------|------|
| URL dạng IP số | 0.9 |
| URL shortener (bit.ly, tinyurl, …) | 0.6 |
| URL pattern nghi ngờ (nhiều subdomain, ký tự lạ) | 0.7 |
| URL bình thường | 0.1 |
| Domain trong whitelist | 0.0 |

Danh sách URL shortener và whitelist được định nghĩa trong [src/config.py](../src/config.py) (`URL_SHORTENERS`, `TRUSTED_DOMAINS`).

**Sender domain risk (10 %)**

| Trường hợp | Điểm |
|------------|------|
| Thuộc `TRUSTED_DOMAINS` | 0.0 |
| Unknown | 0.2 |
| Pattern nghi ngờ | 0.5 |

### 6.2 Quy tắc phân loại 3 mức

```python
SUSPICIOUS_MARGIN = 0.2

if ensemble_score < threshold:                   # 0.6
    classification = "LEGITIMATE"
elif ensemble_score < threshold + SUSPICIOUS_MARGIN:  # 0.8
    classification = "SUSPICIOUS"
else:
    classification = "PHISHING"
```

---

## 7. File `models/*`

### 7.1 `model.joblib`

Lưu dictionary:

```python
{
    "model":         <sklearn Pipeline>,
    "threshold":     0.6,
    "feature_cols":  ["text", "has_attachment", "links_count", "urgent_keywords",
                      "body_length", "exclamation_count", "sender_domain"],
    "label_mapping": {"0": "legitimate", "1": "phishing"},
}
```

### 7.2 `metadata.json`

```json
{
  "num_datasets": 2,
  "num_samples": 410674,
  "feature_cols": ["text", "has_attachment", "links_count", "urgent_keywords",
                   "body_length", "exclamation_count", "sender_domain"],
  "optimal_threshold": 0.6,
  "optimal_f1_score": 0.9577,
  "label_distribution": { "0.0": 212284, "1.0": 198390 },
  "n_phishing": 198390,
  "n_legit": 212284,
  "scale_pos_weight": 1.07
}
```

### 7.3 Baseline `*.joblib`

- `logistic_regression.joblib` — Baseline tuyến tính, dùng để so sánh.
- `random_forest.joblib` — Baseline non-linear.
- `xgboost.joblib` — Baseline XGBoost đơn lẻ (không phải pipeline hoàn chỉnh).

---

## 8. Predict pipeline

File [src/predict.py](../src/predict.py) là entry point CLI cho inference.

### 8.1 Luồng xử lý

```python
# 1. Load model pipeline + metadata
data       = joblib.load(MODEL_PATH)
model      = data["model"]
threshold  = data["threshold"]

# 2. Chuẩn bị feature
X = prepare_features(
    text=raw_text,
    has_attachment=..., links_count=...,
    sender_domain=..., urgent_keywords=...,
    body_length=..., exclamation_count=...,
)

# 3. Model probability
proba_phishing = model.predict_proba(X)[0][1]

# 4. Ensemble score
ensemble_score = calculate_ensemble_score(
    model_proba=proba_phishing,
    urgent_keywords=..., links_count=...,
    sender_domain=...,
)

# 5. Classification
if ensemble_score < threshold:
    classification = "LEGITIMATE"
elif ensemble_score < threshold + SUSPICIOUS_MARGIN:
    classification = "SUSPICIOUS"
else:
    classification = "PHISHING"
```

### 8.2 Định dạng output

```python
{
    "prediction": 0 | 1,
    "classification": "LEGITIMATE" | "SUSPICIOUS" | "PHISHING",
    "proba_phishing": 0.123,
    "ensemble_score": 0.456,
    "threshold": 0.6,
    "suspicious_margin": 0.2,
    "formula_details": { ... },     # Breakdown của ensemble
    "features":         { ... },    # Feature đã trích xuất
    "suspicious_segments": [ ... ], # Top 10 đoạn nghi ngờ
}
```

### 8.3 Suspicious segments

- Email được cắt thành câu (rule-based theo dấu câu).
- Chấm điểm từng câu dựa trên: urgent keyword, URL, pattern (yêu cầu password, phần thưởng lớn, yêu cầu khẩn…).
- Trả về 10 câu điểm cao nhất, kèm `score`, `severity`, `reasons`.

---

## 9. Huấn luyện lại model

### 9.1 Lệnh training

```bash
python -m src.train \
    --data-dir data \
    --text-col body \
    --label-col label \
    --out models
```

### 9.2 Các bước của `train.py`

1. `load_any()` toàn bộ file trong `data-dir`, hợp nhất và `normalize_columns()`.
2. `auto_detect_columns()` tìm `text_col` / `label_col` nếu chưa chỉ định.
3. `coerce_label()` chuẩn hoá nhãn về `{0, 1}`.
4. Tiền xử lý text (`normalize_text`) và auto-extract 6 feature phụ nếu thiếu.
5. `train_test_split` 80/20, `stratify=y`.
6. Build pipeline (`ColumnTransformer + XGBClassifier`).
7. `fit(X_train, y_train)` với `scale_pos_weight` tự tính.
8. Đánh giá trên tập test, quét threshold để tối đa F1.
9. Serialize:
   - `models/model.joblib` (pipeline + metadata)
   - `models/metadata.json`
   - Bản báo cáo `EVALUATION_REPORT` (nếu script tương ứng chạy).

### 9.3 Makefile

```bash
make install         # pip install -r requirements.txt
make install-uv      # uv venv && uv pip install -e .
make init-db         # Khởi tạo DB backend
make run             # Chạy FastAPI dev
make dev             # uvicorn --reload
make test            # Chạy pytest
make test-api        # Chạy script test endpoint
make generate-openapi
```

---

## 10. Thư viện phụ thuộc

Nội dung [requirements.txt](../requirements.txt):

```
joblib>=1.3.0
scikit-learn>=1.3.0
pandas>=2.0.0
beautifulsoup4>=4.12.0
numpy>=1.24.0
scipy>=1.11.0
xgboost>=2.0.0
```

Dependency cho training và inference; backend FastAPI có thêm gói riêng (xem `pyproject.toml`).

---

## 11. Scripts hỗ trợ

Thư mục [scripts/](../scripts/) chứa các tiện ích phục vụ nghiên cứu và vận hành:

| Script | Mục đích |
|--------|---------|
| `analyze_dataset.py` | Phân tích phân phối nhãn và mẫu email |
| `analyze_patterns.py` | So sánh pattern giữa phishing và legitimate |
| `analyze_text_length.py` | Thống kê độ dài email |
| `check_labels.py` | Validate định dạng nhãn |
| `compare_models.py` | So sánh XGBoost / Random Forest / Logistic Regression |
| `generate_evaluation_report.py` | Sinh báo cáo đánh giá tập train/test |
| `show_features.py` | Hiển thị feature đã trích xuất cho một email |
| `prepare_dataset.py` | Chuẩn bị dataset trước training |
| `view_dataset.py` | Xem nhanh nội dung dataset |
| `test_api.py` | Test các endpoint backend |
| `generate_openapi.py` | Xuất OpenAPI schema |
| `init_database.py` | Khởi tạo DB backend |

---

## 12. Tích hợp với backend

- Backend nạp model thông qua biến môi trường `MODEL_PATH` (mặc định `models/model.joblib`).
- [app/services/prediction_service.py](../app/services/prediction_service.py) lazy-load pipeline, lấy `threshold`, `suspicious_margin`, `feature_cols` từ metadata của model.
- Khi phân tích, backend gọi `PredictionService.predict(email_text, ...)` — nội bộ thực hiện đúng pipeline mô tả ở mục 8.
- Kết quả trả về trùng khớp format ở mục 8.2 và được persist vào bảng `predictions`, `prediction_features`, `prediction_links`, `suspicious_segments` (xem [docs/BACKEND.md](./BACKEND.md)).

---

## 13. Tóm tắt

- **Bài toán:** phân loại nhị phân phishing / legitimate, nhưng mở rộng sang 3 mức nguy hiểm nhờ ensemble scoring.
- **Model:** XGBoost (`n_estimators=400`, `max_depth=5`) kết hợp TF-IDF + feature số + sender domain.
- **Hiệu năng:** F1 = 0.9577 tại threshold 0.6 trên 82 k mẫu test (20 % của 410 k).
- **Ensemble:** 0.55 · model + 0.20 · urgent + 0.15 · links + 0.10 · sender.
- **Output giải thích được:** kèm `formula_details` và `suspicious_segments` để người dùng thấy rõ lý do phân loại.
- **Triển khai:** đóng gói qua `joblib`, load lazily trong backend FastAPI.

---

## 14. Chi tiết triển khai

Phần này đi sâu vào mã nguồn trong [src/](../src/) — các hàm, công thức, ví dụ cụ thể và hướng dẫn debug. Sơ đồ tuần tự của luồng predict và scheduler analyze xem [SEQUENCE_DIAGRAMS.md](./SEQUENCE_DIAGRAMS.md).

### 14.1 Hằng số trong `src/config.py`

```python
TRUSTED_DOMAINS = {
    "spktfpt.online",
    # Có thể thêm: "company.com", "partner.vn", ...
}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co",
    "cutt.ly", "short.io", "tiny.cc", "ow.ly",
    "is.gd", "buff.ly", "adf.ly",
}

URGENT_KEYWORDS = {
    "urgent", "immediately", "action required", "verify", "confirm",
    "expire", "expired", "warning", "alert", "locked", "blocked",
    "unauthorized", "refund", "invoice", "payment overdue",
    "password reset", "credential", "click here", "winner",
    "prize", "reward", "congratulations", "bank account",
    "social security", "suspended",
    # ... tổng cộng >60 keyword
}

IP_URL_RE       = re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/|$)")
SUSPICIOUS_TLDS = {".zip", ".top", ".xyz", ".mov", ".click", ".tk"}

SUSPICIOUS_MARGIN = 0.2
```

### 14.2 `text_cleaning.py` — mã nguồn các hàm chính

```python
from bs4 import BeautifulSoup
import re

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)

def strip_html(text: str) -> str:
    try:
        return BeautifulSoup(text, "html.parser").get_text(" ")
    except Exception:
        return text

def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    s = strip_html(str(text))
    s = s.replace("\x00", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def count_urls(text: str) -> int:
    return len(URL_RE.findall(text or ""))

def extract_link_domains(text: str) -> list[str]:
    domains = []
    for url in URL_RE.findall(text or ""):
        try:
            host = urlparse(url).hostname or ""
            if host:
                domains.append(host.lower())
        except Exception:
            pass
    return domains

def exclamation_count(text: str) -> int:
    return (text or "").count("!")

def detect_urgent_keywords(text: str) -> int:
    low = (text or "").lower()
    return int(any(kw in low for kw in URGENT_KEYWORDS))

def detect_attachment_mention(text: str) -> int:
    low = (text or "").lower()
    markers = ("attachment", "attached", "see attached",
               "please find attached", "invoice.pdf", ".docx", ".xlsx", ".zip")
    return int(any(m in low for m in markers))

def extract_sender_domain(text: str) -> str:
    m = re.search(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", text or "")
    return (m.group(1).lower() if m else "unknown")
```

### 14.3 Pipeline trong `features.py`

```python
NUMERIC_COLS = ["has_attachment", "links_count", "urgent_keywords",
                "body_length", "exclamation_count"]

def build_pipeline(scale_pos_weight: float = 1.0) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                min_df=2,
                sublinear_tf=True,
                strip_accents="unicode",
            ), "text"),
            ("numeric",    StandardScaler(),                NUMERIC_COLS),
            ("categorical", OneHotEncoder(handle_unknown="ignore"),
                            ["sender_domain"]),
        ],
        remainder="drop",
        sparse_threshold=0.5,
    )

    clf = XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=5,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.5,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        tree_method="hist",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("clf", clf)])
```

### 14.4 `prepare_features` — input cho inference

```python
def prepare_features(
    text: str,
    has_attachment: int = 0,
    links_count: int = 0,
    sender_domain: str = "unknown",
    urgent_keywords: int = 0,
    body_length: int = 0,
    exclamation_count: int = 0,
) -> pd.DataFrame:
    return pd.DataFrame([{
        "text":              text,
        "has_attachment":    int(has_attachment),
        "links_count":       int(links_count),
        "urgent_keywords":   int(urgent_keywords),
        "body_length":       int(body_length or len(text)),
        "exclamation_count": int(exclamation_count),
        "sender_domain":     sender_domain or "unknown",
    }], columns=FEATURE_COLS)
```

### 14.5 Công thức ensemble — chi tiết

Hàm phân loại từng URL:

```python
def classify_link(url: str) -> float:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return 0.5
    host = host.lower()
    if host in TRUSTED_DOMAINS:
        return 0.0
    if IP_URL_RE.match(url):
        return 0.9
    if host in URL_SHORTENERS:
        return 0.6
    if any(url.endswith(tld) for tld in SUSPICIOUS_TLDS):
        return 0.7
    if host.count("-") >= 3 or host.count(".") >= 4:
        return 0.6
    return 0.1
```

Tổng hợp link risk:

```python
def aggregate_link_risk(urls: list[str]) -> float:
    if not urls:
        return 0.0
    scores = [classify_link(u) for u in urls]
    return sum(scores) / len(scores)
```

Rủi ro sender domain:

```python
def sender_domain_risk(domain: str) -> float:
    if not domain or domain == "unknown":
        return 0.2
    if domain in TRUSTED_DOMAINS:
        return 0.0
    if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
        return 0.5
    return 0.2
```

Công thức cuối:

```python
ensemble_score = (
    0.55 * model_proba
  + 0.20 * float(urgent_flag)
  + 0.15 * aggregate_link_risk(urls)
  + 0.10 * sender_domain_risk(sender_domain)
)
```

### 14.6 Phân loại 3 mức

```python
def classify_threat_level(score: float, threshold: float = 0.6,
                          margin: float = 0.2) -> str:
    if score < threshold:
        return "LEGITIMATE"
    if score < threshold + margin:
        return "SUSPICIOUS"
    return "PHISHING"
```

### 14.7 Trích xuất đoạn nghi ngờ (`suspicious_segments`)

```python
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

SEGMENT_RULES = [
    ("urgent_keyword", 40, lambda s: detect_urgent_keywords(s)),
    ("contains_url",   25, lambda s: count_urls(s) > 0),
    ("deadline",       20, lambda s: bool(re.search(
        r"\b(within|before|until)\s+\d+\s*(hour|hours|day|days)\b", s, re.I))),
    ("money",          15, lambda s: bool(re.search(
        r"\$|€|£|USD|EUR|transfer|wire", s, re.I))),
    ("credential",     30, lambda s: bool(re.search(
        r"\b(password|credential|login|verify account|ssn)\b", s, re.I))),
    ("many_exclaim",   10, lambda s: s.count("!") >= 3),
]

def extract_segments(text: str, top_k: int = 10) -> list[dict]:
    sents = SENTENCE_RE.split(text or "")
    scored = []
    for s in sents:
        s_clean = s.strip()
        if len(s_clean) < 20:
            continue
        score   = 0.0
        reasons = []
        for name, weight, rule in SEGMENT_RULES:
            if rule(s_clean):
                score += weight
                reasons.append(name)
        if score == 0:
            continue
        severity = ("HIGH" if score >= 60 else
                    "MEDIUM" if score >= 30 else "LOW")
        scored.append({
            "text":     s_clean[:400],
            "score":    round(score, 2),
            "severity": severity,
            "reasons":  reasons,
        })
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]
```

### 14.8 Tìm threshold tối ưu trong `train.py`

```python
def find_optimal_threshold(y_true, y_proba, lo=0.3, hi=0.7, step=0.05):
    best_t, best_f1 = 0.5, 0.0
    for t in np.arange(lo, hi + 1e-9, step):
        y_pred = (y_proba >= t).astype(int)
        f1 = f1_score(y_true, y_pred, pos_label=1)
        if f1 > best_f1:
            best_f1, best_t = f1, float(t)
    return best_t, best_f1
```

Sau đó `train.py` ghi ra:

```python
joblib.dump({
    "model":         pipeline,
    "threshold":     best_t,
    "feature_cols":  FEATURE_COLS,
    "label_mapping": {"0": "legitimate", "1": "phishing"},
}, f"{out_dir}/model.joblib")

with open(f"{out_dir}/metadata.json", "w") as f:
    json.dump({
        "num_samples":           len(df),
        "feature_cols":          FEATURE_COLS,
        "optimal_threshold":     best_t,
        "optimal_f1_score":      best_f1,
        "label_distribution":    dict(pd.Series(y).value_counts()),
        "n_phishing":            int((y == 1).sum()),
        "n_legit":               int((y == 0).sum()),
        "scale_pos_weight":      scale_pos_weight,
    }, f, indent=2)
```

### 14.9 Ví dụ end-to-end

**Input email (thô):**
```
Subject: URGENT: Your account has been locked!!!
From: security@paypa1.com

Dear customer,
Your account will be suspended within 24 hours unless you verify
your credentials at http://bit.ly/verify-now
Please find invoice.pdf attached.
```

**Feature trích xuất tự động:**
```python
{
  "text":              "Dear customer, Your account will be suspended ...",
  "has_attachment":    1,     # "attached" + "invoice.pdf"
  "links_count":       1,     # bit.ly
  "urgent_keywords":   1,     # "urgent", "within", "verify", "credential"
  "body_length":       185,
  "exclamation_count": 3,
  "sender_domain":     "paypa1.com"
}
```

**Tính toán:**
```
model_proba = 0.91
urgent      = 1.0
link_risk   = classify_link("http://bit.ly/verify-now") = 0.6
domain_risk = "paypa1.com" not trusted → 0.2

ensemble = 0.55*0.91 + 0.20*1.0 + 0.15*0.6 + 0.10*0.2
        = 0.5005 + 0.2000 + 0.0900 + 0.0200
        = 0.8105

0.8105 >= 0.6 + 0.2 → PHISHING
```

**Suspicious segments (rút gọn):**
```json
[
  {"text": "Your account will be suspended within 24 hours unless you verify your credentials at http://bit.ly/verify-now",
   "score": 115, "severity": "HIGH",
   "reasons": ["urgent_keyword","contains_url","deadline","credential"]},
  {"text": "URGENT: Your account has been locked!!!",
   "score": 50, "severity": "MEDIUM",
   "reasons": ["urgent_keyword","many_exclaim"]}
]
```

### 14.10 So sánh baseline

Thư mục `models/` giữ 3 model để phục vụ ablation:

| Model | File | Mục đích |
|-------|------|---------|
| Logistic Regression | `logistic_regression.joblib` | Baseline tuyến tính |
| Random Forest | `random_forest.joblib` | Baseline non-linear |
| XGBoost đơn | `xgboost.joblib` | Không bao gồm ColumnTransformer |
| XGBoost Pipeline (production) | `model.joblib` | **Dùng trong backend** |

Script `scripts/compare_models.py` load 3 model và in bảng so sánh Accuracy / Precision / Recall / F1 / ROC-AUC.

### 14.11 Debug & Troubleshooting

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|-------------|-----------------------|------------|
| `predict_proba` trả NaN | `sender_domain` là `None` | Luôn truyền `"unknown"` mặc định |
| F1 giảm đột ngột sau retrain | Dataset mất cân bằng hoặc `stratify` không hoạt động | Kiểm tra `label_distribution` trong `metadata.json`, đảm bảo `scale_pos_weight` được set |
| Classification luôn là PHISHING | Threshold không được load | Kiểm tra `data["threshold"]` trong `joblib.load(...)` |
| OneHotEncoder báo lỗi ở runtime | Domain mới chưa từng thấy | `handle_unknown="ignore"` đã được bật; nếu vẫn lỗi → upgrade sklearn |
| TF-IDF chậm khi input dài | `max_features=5000` đủ nhưng vẫn fit toàn bộ text | Truncate email > 50k ký tự trước khi gọi predict |

### 14.12 Tham chiếu sơ đồ tuần tự

| Luồng | Diagram |
|-------|---------|
| Predict từ text paste | [8](./SEQUENCE_DIAGRAMS.md#8-phân-tích-email-thủ-công-paste-text) |
| Scheduler phân tích email | [6](./SEQUENCE_DIAGRAMS.md#6-scheduler--job-phân-tích-email-định-kỳ) |
| Dịch + phân tích bản dịch | [9](./SEQUENCE_DIAGRAMS.md#9-dịch--phân-tích-bản-dịch) |
| Bulk analyze | [12](./SEQUENCE_DIAGRAMS.md#12-bulk-analyze-frontend) |
