# Phishing Email Detection System (AI-based)

## 1. Overview

This project implements an AI-based Phishing Email Detection System using supervised machine learning.
The system is designed with a strong emphasis on **system engineering and dataset management** rather than
model accuracy alone.

A key contribution of this system is the **Dataset Memory architecture**, which allows the model to be trained
on multiple heterogeneous datasets without manual file merging and without losing knowledge from previously
used datasets.

The system operates entirely via **command-line interface (PowerShell / Terminal)** and does not depend on
external tools or services.

---

## 2. Key Features

- Automatic loading of **all dataset files in a directory**
- Support for **CSV and Excel** datasets
- **Dataset memory** through historical dataset retention (system-level memory)
- Retraining on accumulated datasets (old + new)
- Command-line prediction (text or file-based)
- Probabilistic phishing risk output
- Automatic detection and normalization of text and label columns
- Robust handling of real-world dataset inconsistencies

---

## 3. Project Structure

```
Final_Project_FPTU/
├── src/
│   ├── __init__.py
│   ├── train.py          # Training pipeline with dataset memory
│   ├── predict.py        # Phishing prediction module
│   ├── features.py       # TF-IDF + XGBoost pipeline
│   ├── data_io.py        # CSV / Excel loader
│   ├── label_utils.py    # Label normalization
│   └── text_cleaning.py  # Text preprocessing
│
├── data/
│   ├── incoming/         # New datasets (user input)
│   ├── history/          # Cached datasets (dataset memory)
│   └── runtime_cache/    # Reserved for future use
│
├── models/
│   ├── model.joblib
│   └── metadata.json
│
├── samples/              # Sample email files for testing
├── README.md
└── README_VI.md
```

---

## 4. Dataset Handling Strategy

### 4.1 Automatic Dataset Ingestion

The system automatically scans the `data/incoming/` directory and loads **all compatible dataset files**
without requiring manual file merging.

Supported formats:

- CSV (`.csv`)
- Excel (`.xlsx`)

Datasets are merged **in memory only during training**, ensuring clean data management.

---

### 4.2 Dataset Memory (Historical Knowledge Retention)

The model itself does **not** memorize past datasets.
Instead, dataset persistence is handled at the **system level** via the `data/history/` directory.

Training behavior:

1. New datasets are cached into `data/history/`
2. All historical datasets are loaded during training
3. The model is retrained from scratch using accumulated data

This design follows correct machine learning principles and aligns with real-world **MLOps practices**.

---

## 5. Training the Model

### 5.1 Train Using All Datasets in a Folder

```bash
python -m src.train --data-dir data --text-col body --label-col label
```

### 5.2 Force Text and Label Columns (For Unusual Datasets)

```bash
python -m src.train --data-dir data --text-col email_text --label-col is_phishing
```

---

## 6. Training Outputs

After training, the following artifacts are generated:

```
models/
├── model.joblib
└── metadata.json
```

The metadata file includes:

- Number of datasets used
- Number of samples
- Label distribution
- Evaluation metrics

---

## 7. Command-Line Prediction Demo

### Predict Phishing Email

```bash
python -m src.predict --text "Urgent: Verify your bank account immediately"
```

### Predict Benign Email

```bash
python -m src.predict --text "Team meeting at 10 AM tomorrow"
```

### Predict from Email File

```bash
python -m src.predict --file samples/phishing.txt
```

### JSON Output (Integration Mode)

```bash
python -m src.predict --file samples/phishing.txt --json
```

---

## 8. Model Architecture

- Text preprocessing (normalization, cleaning)
- TF-IDF feature extraction (unigrams and bigrams)
- XGBoost classifier

**Reasons for choosing XGBoost:**

- Strong performance on sparse text features
- Fast training and inference
- Robust against overfitting
- Well-suited for academic projects

---

## 9. System Limitations

- Batch learning only (no online learning)
- Requires retraining for new data
- Marketing emails may cause false positives
- Datasets are primarily in English

These limitations are documented and acceptable for academic purposes.

---

## 10. Conclusion

This system demonstrates a practical and extensible phishing email detection pipeline with:

- Flexible dataset handling
- Historical knowledge retention
- Clean command-line usability
- Strong alignment with real-world ML engineering practices

The project is well-suited for **final-year academic evaluation** and real-world demonstrations.
