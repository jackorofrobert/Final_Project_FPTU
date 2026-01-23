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
├── src/
│   ├── __init__.py
│   ├── train.py
│   ├── predict.py
│   ├── features.py
│   ├── data_io.py
│   ├── label_utils.py
│   └── text_cleaning.py
│
├── app/
│   └── main.py
│
├── data/
│   ├── incoming/
│   ├── history/
│   └── runtime_cache/
│
├── models/
│   ├── model.joblib
│   └── metadata.json
│
├── samples/
├── requirements.txt
├── README.md
└── README_VI.md
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
```

---

## 8. Machine Learning Model

- TF-IDF feature extraction
- XGBoost classifier

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
