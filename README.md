# Phishing Email Detection System (AI-based)

## 1. Overview

This project implements an AI-based phishing email detection system using supervised machine learning.
The system automatically ingests multiple datasets, retains historical knowledge through dataset memory,
and performs phishing detection via command-line interface without any external tools.

The model classifies emails as phishing or benign and returns a probability score indicating phishing risk.

---

## 2. Key Features

- Automatic loading of all dataset files in a folder (CSV, Excel, JSON)
- Dataset memory through historical data retention (system-level memory)
- Retraining on accumulated datasets
- Command-line prediction (PowerShell / Terminal)
- Probabilistic output for decision support
- Auto-detection of text and label columns (with manual override)

---

## 3. Project Structure

```
Final_FPTU/
├── src/
│   ├── train.py
│   ├── predict.py
│   ├── data_io.py
│   ├── text_cleaning.py
│   ├── features.py
│   └── config.py
│
├── data/
│   ├── incoming/        # New datasets (user input)
│   ├── history/         # Cached datasets (model memory)
│   └── runtime_cache/   # Internal use
│
├── models/
│   ├── model.joblib
│   └── metadata.json
│
└── README.md
```

---

## 4. Dataset Handling Strategy

### 4.1 Automatic Dataset Ingestion

The system scans the entire data directory and automatically loads all compatible dataset files.
Datasets are merged in memory only during training; no manual file merging is required.

Supported formats:

- CSV
- Excel (XLSX, XLS)
- JSON

---

### 4.2 Dataset Memory (Historical Knowledge Retention)

The model itself does not memorize past datasets.
Instead, the system preserves all previously used datasets in a history directory.

During retraining:

1. Historical datasets are loaded
2. Newly added datasets are included
3. The model is retrained from scratch on accumulated data

This approach ensures correct machine learning behavior and aligns with real-world MLOps practices.

---

## 5. Training the Model

### 5.1 Train Using All Datasets in a Folder

python -m src.train --data-dir data

### 5.2 Force Text and Label Columns

python -m src.train --data-dir data --text-col email_text --label-col is_phishing

### 5.3 Custom Dataset Memory Location (Optional)

python -m src.train --data-dir data --history-dir custom_history/

---

## 6. Training Outputs

After training:

- models/model.joblib
- models/metadata.json

Metrics include F1-score, ROC-AUC, and confusion matrix.

---

## 7. Command-Line Demo

### Predict Phishing Email

python -m src.predict --text "Urgent: Verify your bank account immediately"

### Predict Benign Email

python -m src.predict --text "Team meeting at 10 AM tomorrow"

---

## 8. Model Architecture

- Text preprocessing (HTML removal, normalization)
- TF-IDF feature extraction
- URL-based features
- XGBoost classifier

---

## 9. Limitations

- Batch learning only (no online learning)
- Requires retraining for new data

---

## 10. Conclusion

This system demonstrates a practical phishing detection pipeline with flexible dataset handling,
historical knowledge retention, and command-line usability suitable for academic and real-world use.
