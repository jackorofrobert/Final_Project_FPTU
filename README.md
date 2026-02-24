# Phishing Email Detection System (AI-based)

## 1. Introduction

This project implements an **AI-based Phishing Email Detection System** with a strong focus on system engineering rather than model accuracy alone.

A key contribution of this system is the **Dataset Memory architecture**, which allows the model to be trained on multiple heterogeneous datasets without manual file merging and without losing knowledge from previously used datasets.

The system is suitable for:

- Final-year academic projects
- Security Operations Center (SOC) demonstrations
- Research and experimentation in email security

---

## 2. System Objectives

- Detect phishing and legitimate emails using Machine Learning
- Support training from multiple datasets with different formats
- Handle real-world dataset inconsistencies (column names, labels, structure)
- Allow full training and prediction via command line (PowerShell / Terminal)
- Provide a flexible foundation for future extensions

---

## 3. Overall Architecture

### 3.1 Dataset Memory Architecture

The model itself does not remember previous data. Dataset persistence is handled at the system level.

Workflow:

1. New datasets are placed into data/incoming/
2. Each dataset is hashed and cached into data/history/
3. During training, all cached datasets are loaded
4. The model is retrained using the complete dataset history

Benefits:

- No manual dataset merging
- No data loss across training runs
- Reproducible and extensible training pipeline

---

## 4. Project Structure

```
Final_Project_FPTU/
├── src/                    # Core ML model source code
│   ├── __init__.py
│   ├── train.py           # Training pipeline
│   ├── predict.py         # Prediction module
│   ├── features.py        # Feature engineering
│   ├── data_io.py         # Data loading utilities
│   ├── label_utils.py     # Label normalization
│   ├── text_cleaning.py   # Text preprocessing
│   └── config.py          # Configuration
│
├── app/                    # FastAPI REST API
│   ├── main.py
│   ├── api/
│   ├── services/
│   └── schemas/
│
├── frontend/               # Web interface
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── data/                   # Dataset storage
│   ├── incoming/          # New datasets go here
│   └── history/           # Cached/processed datasets
│
├── models/                 # Trained models
│   ├── model.joblib
│   └── metadata.json
│
├── scripts/                # Analysis & utility scripts
│   ├── analyze_dataset.py
│   ├── analyze_patterns.py
│   ├── analyze_text_length.py
│   ├── check_labels.py
│   └── prepare_dataset.py
│
├── tests/                  # Test files
│   └── test_trusted_domain.py
│
├── docs/                   # Documentation
│   ├── MODEL_DOCUMENTATION.md
│   ├── PHISHING_SCORE_FORMULA.md
│   ├── FEATURE_EXTRACTION_GUIDE.md
│   ├── DATA_CLEANING_GUIDE.md
│   ├── ML_LEARNING_GUIDE.md
│   ├── plan.md
│   ├── api.md
│   └── frontend.md
│
├── samples/                # Sample email files
├── requirements.txt
├── run.py                  # Server entrypoint
└── README.md
```

---

## 5. Dataset Handling and Preprocessing

### 5.1 Supported Dataset Formats

- CSV (.csv)
- Excel (.xlsx)

### 5.2 Automatic Text Column Resolution

Priority:

1. User-specified column (--text-col)
2. body
3. email_text
4. subject
5. Synthesized text from subject + email_text

### 5.3 Label Normalization

- phishing, spam, scam → 1
- legitimate, ham, normal → 0
- numeric labels are preserved

---

## 6. Model Training

```bash
python -m src.train --data-dir data --text-col body --label-col label
```

---

## 7. Prediction

```bash
python -m src.predict --text "Verify your account now"
python -m src.predict --file samples/phishing.txt
python -m src.predict --file samples/phishing.txt --json
```

### Detailed Formula Output

Cả CLI và API đều trả về chi tiết công thức Ensemble:

| Thông tin             | Mô tả                                                                     |
| --------------------- | ------------------------------------------------------------------------- |
| **Model Probability** | Raw score × 70% = contribution                                            |
| **Urgent Keywords**   | 0 hoặc 1 × 12% = contribution                                             |
| **Links Risk**        | Chi tiết từng link (TRUSTED/NORMAL/SHORTENER/IP_BASED/SUSPICIOUS) × 10.5% |
| **Domain Risk**       | Domain → TRUSTED (0%) hoặc SUSPICIOUS (50%) × 7.5%                        |
| **Formula Text**      | Chuỗi công thức đầy đủ                                                    |

> Chi tiết tham khảo: [docs/PHISHING_SCORE_FORMULA.md](docs/PHISHING_SCORE_FORMULA.md)

---

## 8. Machine Learning Model

- **Primary**: XGBoost classifier with TF-IDF features
- **Alternative**: Random Forest, Logistic Regression

### Ensemble Score Formula

```
Score = Model×70% + Urgent×12% + Links×10.5% + Domain×7.5%
```

### Domain Classification (Simple)

- **TRUSTED (0%)**: Domains in your whitelist (`config.py`)
- **SUSPICIOUS (50%)**: All other domains

### Link Classification

| Type       | Risk | Description                  |
| ---------- | ---- | ---------------------------- |
| TRUSTED    | 0%   | Links to whitelisted domains |
| SHORTENER  | 60%  | bit.ly, tinyurl...           |
| IP_BASED   | 90%  | Uses IP instead of domain    |
| SUSPICIOUS | 80%  | Contains phishing patterns   |
| NORMAL     | 10%  | Regular links                |

### Multi-Model Support

```bash
# Train and save all models
python scripts/compare_models.py --save-models

# Predict with different models
python -m src.predict --model models/random_forest.joblib --file email.txt
python -m src.predict --model models/logistic_regression.joblib --file email.txt
```

### Show Feature Extraction

```bash
python scripts/show_features.py --file samples/test.txt
```

---

## 9. Environment Setup

```bash
pip install -r requirements.txt
```

---

## 10. Running the Application

```bash
python -m app
```

---

## 11. System Limitations

- Batch learning only
- Marketing emails may cause false positives
- Primarily English datasets

---

## 12. Conclusion

This system demonstrates a robust and extensible phishing email detection pipeline with strong emphasis on dataset engineering.
