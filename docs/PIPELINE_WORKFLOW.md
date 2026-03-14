# 🔄 Pipeline Workflow — Phishing Email Detection

> **Dự án:** Final Project FPTU | **Cập nhật:** 13/03/2026

---

## 📊 Slide 1 — Tổng Quan: Giai Đoạn Training

```mermaid
flowchart TD
    A["📦 Dataset CSV\ndata/incoming/"] --> B["🧹 Feature Extraction\nsrc/text_cleaning.py"]
    B --> C["⚙️ Feature Pipeline\nTF-IDF + Scaler + OneHot"]
    C --> D["🏋️ Train 3 Models\ncompare_models.py"]
    D --> E1["XGBoost ⭐"]
    D --> E2["Random Forest"]
    D --> E3["Logistic Regression"]
    E1 --> F["💾 model.joblib"]
    E2 -.->|"--save-models"| F
    E3 -.->|"--save-models"| F

    style A fill:#4a90d9,color:#fff
    style F fill:#7b68ee,color:#fff
    style E1 fill:#27ae60,color:#fff
```

---

## 📊 Slide 2 — Tổng Quan: Giai Đoạn Prediction

```mermaid
flowchart TD
    F["💾 model.joblib"] --> G{"📨 Email Input"}
    G -->|"CLI"| H1["python -m src.predict\n--file email.txt"]
    G -->|"Web"| H2["POST /api/v1/\npredictions/analyze"]
    H1 --> I["🔍 Feature Extraction"]
    H2 --> I
    I --> J["🤖 XGBoost predict_proba()"]
    J --> K["📊 Ensemble Scoring"]
    K --> L1["✅ LEGITIMATE\n< 0.50"]
    K --> L2["⚡ SUSPICIOUS\n0.50–0.70"]
    K --> L3["🚨 PHISHING\n≥ 0.70"]

    style F fill:#7b68ee,color:#fff
    style K fill:#e8a838,color:#fff
    style L1 fill:#2ecc71,color:#fff
    style L2 fill:#f39c12,color:#fff
    style L3 fill:#e74c3c,color:#fff
```

---

## 📊 Slide 3 — Feature Extraction: Text → 7 Features

```mermaid
flowchart LR
    RAW["📧 Raw Email Text"] --> N["normalize_text()\nStrip HTML"]
    RAW --> U["count_urls()\n→ links_count"]
    RAW --> UK["detect_urgent_keywords()\n→ urgent_keywords"]
    RAW --> SD["extract_sender_domain()\n→ sender_domain"]
    RAW --> BL["length_chars()\n→ body_length"]
    RAW --> EC["exclamation_count()\n→ exclamation_count"]
    RAW --> HA["detect_attachment_mention()\n→ has_attachment"]

    style RAW fill:#3498db,color:#fff
```

---

## 📊 Slide 4 — Feature Pipeline: Preprocessing

```mermaid
flowchart LR
    N["text\nnormalized"] --> TFIDF["TF-IDF\n5000 features\nbigrams"]
    NUM["5 numeric cols\nhas_attachment\nlinks_count\nurgent_keywords\nbody_length\nexclamation_count"] --> SCALE["StandardScaler"]
    CAT["sender_domain"] --> OHE["OneHotEncoder"]

    TFIDF --> VEC["⚡ Feature Vector"]
    SCALE --> VEC
    OHE --> VEC
    VEC --> CLF["🤖 XGBoost / RF / LR"]

    style VEC fill:#9b59b6,color:#fff
    style CLF fill:#e67e22,color:#fff
```

---

## 📊 Slide 5 — Ensemble Scoring Formula

```mermaid
flowchart TD
    P["🤖 Model proba"] -->|"× 55%"| ES
    UK2["🔑 Urgent keywords\n0 hoặc 1"] -->|"× 20%"| ES
    LR2["🔗 Links Risk"] -->|"× 15%"| ES
    DR["📮 Domain Risk"] -->|"× 10%"| ES
    ES["➕ Ensemble Score"]

    style ES fill:#e8a838,color:#fff
    style P fill:#3498db,color:#fff
```

---

## 📊 Slide 6 — Links & Domain Risk Score

```mermaid
flowchart LR
    L["🔗 URL trong email"] --> C1{"Phân loại"}
    C1 -->|"Trong whitelist"| T["TRUSTED → 0.0"]
    C1 -->|"Bình thường"| N["NORMAL → 0.1"]
    C1 -->|"bit.ly, tinyurl..."| S["SHORTENER → 0.6"]
    C1 -->|"verify/login/secure"| SUS["SUSPICIOUS → 0.7"]
    C1 -->|"http://1.2.3.4/..."| IP["IP-BASED → 0.9"]

    D["📮 Sender Domain"] --> C2{"Phân loại"}
    C2 -->|"Trong whitelist"| DT["TRUSTED → 0.0"]
    C2 -->|"Không có trong whitelist"| DU["UNKNOWN → 0.5"]

    style T fill:#2ecc71,color:#fff
    style N fill:#95a5a6,color:#fff
    style S fill:#f39c12,color:#fff
    style SUS fill:#e67e22,color:#fff
    style IP fill:#e74c3c,color:#fff
    style DT fill:#2ecc71,color:#fff
    style DU fill:#e67e22,color:#fff
```

---

## 📊 Slide 7 — Web Flow: Đăng nhập Gmail

```mermaid
sequenceDiagram
    actor User as 👤 User
    participant FE as 🌐 Web Frontend
    participant API as 🔐 Auth API
    participant Gmail as 📧 Gmail OAuth2
    participant DB as 🗄️ SQLite DB

    User->>FE: Click "Connect Gmail"
    FE->>API: GET /auth/gmail/login
    API->>Gmail: Redirect OAuth2
    Gmail-->>User: Màn hình cấp quyền
    User->>Gmail: Chấp nhận
    Gmail-->>API: Callback + auth_code
    API->>Gmail: Exchange → access_token
    API->>DB: Lưu token
    API-->>FE: Set JWT cookie
    FE-->>User: ✅ Đã kết nối
```

---

## 📊 Slide 8 — Web Flow: Fetch & Phân tích Inbox

```mermaid
sequenceDiagram
    actor User as 👤 User
    participant FE as 🌐 Frontend
    participant API as 📧 Email API
    participant Gmail as 📬 Gmail
    participant DB as 🗄️ DB

    User->>FE: Click "Fetch & Analyze"
    FE->>API: GET /emails (JWT)
    API->>Gmail: Fetch inbox
    Gmail-->>API: Danh sách email
    API->>DB: Lưu emails
    API-->>FE: Email list
    FE-->>User: Hiển thị danh sách inbox
```

---

## 📊 Slide 9 — Web Flow: Gọi Model Predict

```mermaid
sequenceDiagram
    actor User as 👤 User
    participant FE as 🌐 Frontend
    participant Pred as 🤖 Prediction API
    participant Svc as ⚙️ PredictionService
    participant Model as 💾 XGBoost
    participant DB as 🗄️ DB

    User->>FE: Click phân tích email
    FE->>Pred: POST /analyze-email/{id}
    Pred->>DB: Load email (body+subject+sender)
    Pred->>Svc: predict(text, subject, sender)
    Svc->>Svc: Feature extraction
    Svc->>Model: predict_proba(X)
    Model-->>Svc: proba_phishing
    Svc->>Svc: Ensemble Scoring
    Svc-->>Pred: result dict
    Pred->>DB: Lưu prediction
    Pred-->>FE: JSON response
    FE-->>User: 🚨 PHISHING / ⚡ SUSPICIOUS / ✅ LEGITIMATE
```

---

## 📊 Slide 10 — Web Flow: Phân tích Email Thủ Công

```mermaid
sequenceDiagram
    actor User as 👤 User
    participant FE as 🌐 Frontend
    participant Pred as 🤖 Prediction API
    participant Svc as ⚙️ PredictionService
    participant Model as 💾 XGBoost

    User->>FE: Paste email text
    FE->>Pred: POST /analyze (email_text, subject)
    Pred->>Svc: predict(text, subject)
    Svc->>Svc: Feature extraction + Ensemble
    Svc->>Model: predict_proba(X)
    Model-->>Svc: proba
    Svc-->>Pred: result
    Pred-->>FE: JSON
    FE-->>User: Kết quả + chi tiết scoring
```

---

## 🗂️ Tóm tắt lệnh

```bash
# Train & compare
python scripts/compare_models.py

# Train production model
python -m src.train

# Predict CLI
python -m src.predict --file samples/01_paypal_suspension.txt

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```
