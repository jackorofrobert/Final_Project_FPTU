# Phishing Email Detection System (AI-based)

## 1. Introduction

This project implements an **AI-based Phishing Email Detection System** using Machine Learning.  
The system is designed to be **flexible and reusable**, allowing retraining with different datasets **without modifying source code**.

The model uses **supervised learning** to classify emails as **phishing** or **benign**, and returns a **probability score** for phishing risk.

---

## 2. Project Structure

Final_FPTU/
├── src/
│ ├── train.py # Train model
│ ├── predict.py # Predict phishing email
│ ├── data_io.py # Data loading & preprocessing
│ ├── text_cleaning.py # Text normalization & HTML cleaning
│ ├── features.py # Feature extraction (TF-IDF + URL features)
│ └── config.py # Global configuration
│
├── data/
│ ├── phishing_email_dataset.xlsx # Original Excel dataset
│ └── clean_phishing_dataset.csv # Clean dataset for training
│
├── models/
│ ├── model.joblib # Trained model
│ └── metadata.json # Evaluation metrics
│
└── README.md

---

## 3. Requirements

- Python **>= 3.9**

### Required Libraries

- pandas
- scikit-learn
- xgboost
- joblib
- openpyxl
- beautifulsoup4

### Install Dependencies

```bash
pip install pandas scikit-learn xgboost joblib openpyxl beautifulsoup4

4. Dataset Description

The dataset contains phishing and benign email samples with the following fields:

Column	Description
body	Email content
label	Classification label
Label Encoding

1 → Phishing

0 → Benign

The original dataset is stored in Excel format and converted to a clean CSV file before training.

5. Convert Excel Dataset to Clean CSV

To avoid CSV corruption caused by Excel encoding issues, the dataset is converted using Python:

import pandas as pd

df = pd.read_excel("data/phishing_email_dataset.xlsx")
df.columns = [c.strip().lower() for c in df.columns]
df = df[["body", "label"]]

df.to_csv("data/clean_phishing_dataset.csv", index=False, encoding="utf-8")
print("Clean dataset created")

6. Training the Model

Train the phishing detection model using the clean CSV dataset:

python -m src.train \
  --data data/clean_phishing_dataset.csv \
  --text-col body \
  --label-col label

Output Files

After training, the following files will be generated:

models/
├── model.joblib
└── metadata.json

7. Predicting Phishing Emails
7.1 Predict via Command Line
python -m src.predict \
  --model models/model.joblib \
  --text "Urgent: Verify your bank account immediately"

Example Output
{
  "pred": 1,
  "proba_phishing": 0.93,
  "threshold": 0.5
}

7.2 Prediction Meaning
Field	Meaning
pred	1 = phishing, 0 = benign
proba_phishing	Probability of phishing
threshold	Decision threshold
8. Using a Different Dataset

The system supports retraining with any compatible dataset.

8.1 CSV Dataset
python -m src.train \
  --data data/new_dataset.csv \
  --text-col email_text \
  --label-col is_phishing

8.2 Excel Dataset

Convert Excel to CSV using Python

Train the model with the converted CSV file

8.3 Dataset Without Labels

If the dataset does not contain labels:

❌ Model cannot be retrained

✅ Existing trained model can still be used for prediction

9. Model Architecture
9.1 Text Preprocessing

HTML tag removal

Lowercasing

Text normalization

9.2 Feature Extraction

TF-IDF (word & n-grams)

URL-based features

9.3 Classifier

XGBoost (XGBClassifier)

XGBoost is chosen for:

Strong performance on sparse text features

Robustness against overfitting

Fast training and inference

10. Demo Workflow
10.1 Verify Trained Model
dir models

10.2 Predict Phishing Email
python -m src.predict \
  --model models/model.joblib \
  --text "Urgent security alert"

10.3 Predict Benign Email
python -m src.predict \
  --model models/model.joblib \
  --text "Team meeting at 10 AM tomorrow"

11. Conclusion

This project demonstrates a practical AI-based phishing email detection system that:

Can be retrained with different datasets

Produces probabilistic predictions

Is suitable for real-world email security integration

12. Future Improvements

Web-based demo using Flask or FastAPI
Integration with email servers (SMTP / IMAP)
Advanced NLP models (BERT, RoBERTa)
Continuous learning with new phishing samples
```
