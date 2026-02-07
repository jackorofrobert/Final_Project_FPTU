# -*- coding: utf-8 -*-
# So sanh hieu suat cua 3 mo hinh phan loai:
# 1. XGBoost (Mo hinh chinh cua du an)
# 2. Random Forest (Baseline 1)
# 3. Logistic Regression (Baseline 2)
#
# Chay script:
#     cd c:\Users\LTT\Desktop\Final_Project_FPTU
#     python scripts/compare_models.py
#     python scripts/compare_models.py --save-models  # Luu ca 3 model

import sys
import time
import warnings
import argparse
from pathlib import Path
from joblib import dump

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, classification_report, confusion_matrix
)
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

# Suppress warnings
warnings.filterwarnings('ignore')

# Set encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# =========================
# Feature Configuration
# =========================
TEXT_COL = 'text'
NUMERIC_COLS = ['has_attachment', 'links_count', 'urgent_keywords', 'body_length', 'exclamation_count']
CATEGORICAL_COLS = ['sender_domain']
FEATURE_COLS = [TEXT_COL] + NUMERIC_COLS + CATEGORICAL_COLS


def build_preprocessor():
    """Build feature preprocessing pipeline (shared by all models)"""
    
    text_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            lowercase=True,
            stop_words="english"
        ))
    ])
    
    numeric_pipeline = Pipeline([
        ('scaler', StandardScaler())
    ])
    
    categorical_pipeline = Pipeline([
        ('onehot', OneHotEncoder(
            handle_unknown='ignore',
            sparse_output=False
        ))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('text', text_pipeline, TEXT_COL),
            ('numeric', numeric_pipeline, NUMERIC_COLS),
            ('categorical', categorical_pipeline, CATEGORICAL_COLS)
        ],
        remainder='drop'
    )
    
    return preprocessor


def build_model_pipeline(model_name: str):
    """Build complete pipeline with specified classifier"""
    
    preprocessor = build_preprocessor()
    
    if model_name == "XGBoost":
        clf = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            use_label_encoder=False,
            random_state=42,
            verbosity=0
        )
    elif model_name == "Random Forest":
        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
    elif model_name == "Logistic Regression":
        clf = LogisticRegression(
            max_iter=1000,
            random_state=42,
            n_jobs=-1
        )
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    return Pipeline([
        ("preprocessor", preprocessor),
        ("clf", clf)
    ])


def prepare_data(data_path: Path):
    """Load and prepare dataset"""
    
    print("Loading dataset...")
    df = pd.read_csv(data_path)
    
    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Import text cleaning functions
    from src.text_cleaning import (
        count_urls, detect_urgent_keywords, extract_sender_domain,
        detect_attachment_mention, exclamation_count, length_chars
    )
    
    # Determine text column
    if 'body' in df.columns:
        text_col = 'body'
    elif 'email_text' in df.columns:
        text_col = 'email_text'
    elif 'text' in df.columns:
        text_col = 'text'
    else:
        text_col = df.columns[0]
    
    print(f"Using text column: '{text_col}'")
    text_content = df[text_col].astype(str)
    
    # Create text column
    df[TEXT_COL] = text_content
    
    # Extract features if not present
    if 'has_attachment' not in df.columns:
        print("Extracting 'has_attachment'...")
        df['has_attachment'] = text_content.apply(detect_attachment_mention)
    
    if 'links_count' not in df.columns:
        print("Extracting 'links_count'...")
        df['links_count'] = text_content.apply(count_urls)
    
    if 'urgent_keywords' not in df.columns:
        print("Extracting 'urgent_keywords'...")
        df['urgent_keywords'] = text_content.apply(detect_urgent_keywords)
    
    if 'sender_domain' not in df.columns:
        print("Extracting 'sender_domain'...")
        df['sender_domain'] = text_content.apply(extract_sender_domain)
    
    if 'body_length' not in df.columns:
        print("Extracting 'body_length'...")
        df['body_length'] = text_content.apply(length_chars)
    
    if 'exclamation_count' not in df.columns:
        print("Extracting 'exclamation_count'...")
        df['exclamation_count'] = text_content.apply(exclamation_count)
    
    # Convert types
    df['has_attachment'] = df['has_attachment'].fillna(0).astype(int)
    df['links_count'] = df['links_count'].fillna(0).astype(int)
    df['urgent_keywords'] = df['urgent_keywords'].fillna(0).astype(int)
    df['sender_domain'] = df['sender_domain'].fillna('unknown').astype(str)
    df['body_length'] = df['body_length'].fillna(0).astype(int)
    df['exclamation_count'] = df['exclamation_count'].fillna(0).astype(int)
    
    # Normalize labels
    from src.label_utils import normalize_label
    df['label'] = df['label'].apply(normalize_label)
    
    # Keep only needed columns
    df = df[FEATURE_COLS + ['label']].dropna()
    
    return df


def print_metrics_explanation():
    """Print explanation of metrics"""
    print("\n" + "=" * 80)
    print("                    GIAI THICH CAC CHI SO DANH GIA")
    print("=" * 80)
    print("""
+-------------+----------------------------------------------------------+
| Chi so      | Y nghia                                                  |
+-------------+----------------------------------------------------------+
| Accuracy    | % email duoc phan loai DUNG tren tong so                 |
|             | Cong thuc: (TP + TN) / Total                             |
+-------------+----------------------------------------------------------+
| Precision   | Khi model noi "Phishing", dung bao nhieu %?              |
|             | Cong thuc: TP / (TP + FP)                                |
|             | Cao = it danh nham email hop le thanh spam               |
+-------------+----------------------------------------------------------+
| Recall      | Model bat duoc bao nhieu % email phishing thuc su?       |
|             | Cong thuc: TP / (TP + FN)                                |
|             | Cao = it bo sot email lua dao                            |
+-------------+----------------------------------------------------------+
| F1-Score    | Can bang giua Precision va Recall                        |
|             | Cong thuc: 2 * (Precision * Recall) / (P + R)            |
|             | CHI SO QUAN TRONG NHAT de so sanh model                  |
+-------------+----------------------------------------------------------+

Confusion Matrix:
                      Predicted
                   Legit    Phishing
Actual  Legit       TN        FP      <- FP = False Positive (danh nham)
        Phishing    FN        TP      <- FN = False Negative (bo sot)

- TP (True Positive): Phishing thuc su, du doan Phishing -> DUNG
- TN (True Negative): Hop le thuc su, du doan Hop le -> DUNG
- FP (False Positive): Hop le thuc su, du doan Phishing -> SAI (danh nham)
- FN (False Negative): Phishing thuc su, du doan Hop le -> SAI (bo sot)
""")


def print_comparison_table(results: list):
    """Print comparison table"""
    
    print("\n" + "=" * 90)
    print("                         BANG SO SANH HIEU SUAT 3 MO HINH")
    print("=" * 90)
    
    # Header
    print(f"\n{'Model':<22} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'Train Time':>12}")
    print("-" * 90)
    
    # Data rows
    for r in results:
        print(f"{r['model']:<22} {r['accuracy']:>9.2%} {r['precision']:>9.2%} {r['recall']:>9.2%} {r['f1_score']:>10.4f} {r['train_time']:>10.2f}s")
    
    print("-" * 90)
    
    # Find best model
    best_f1 = max(results, key=lambda x: x['f1_score'])
    print(f"\n>>> MO HINH TOT NHAT theo F1-Score: {best_f1['model']} ({best_f1['f1_score']:.4f})")


def print_confusion_matrix_detail(model_name: str, y_true, y_pred):
    """Print detailed confusion matrix with explanation"""
    
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    total = len(y_true)
    total_legit = (y_true == 0).sum()
    total_phish = (y_true == 1).sum()
    
    print(f"\n{'='*70}")
    print(f"CONFUSION MATRIX: {model_name}")
    print(f"{'='*70}")
    
    print(f"""
                              Du doan (Predicted)
                         Hop le (0)    Phishing (1)
                        +-----------+-----------+
    Thuc te   Hop le (0)|   {tn:6d}  |   {fp:6d}  |  <- {total_legit:,} email hop le
    (Actual)            +-----------+-----------+
              Phish (1) |   {fn:6d}  |   {tp:6d}  |  <- {total_phish:,} email phishing
                        +-----------+-----------+
    """)
    
    print(f"  PHAN TICH CHI TIET:")
    print(f"  - True Negative (TN)  = {tn:,} email hop le duoc nhan dien DUNG")
    print(f"  - True Positive (TP)  = {tp:,} email phishing duoc phat hien DUNG")
    print(f"  - False Positive (FP) = {fp:,} email hop le bi DANH NHAM la phishing")
    print(f"  - False Negative (FN) = {fn:,} email phishing bi BO SOT")
    
    print(f"\n  TY LE LOI:")
    fp_rate = fp / total_legit * 100 if total_legit > 0 else 0
    fn_rate = fn / total_phish * 100 if total_phish > 0 else 0
    print(f"  - Ty le danh nham (FP Rate) = {fp_rate:.2f}% ({fp}/{total_legit})")
    print(f"  - Ty le bo sot (FN Rate)    = {fn_rate:.2f}% ({fn}/{total_phish})")


def print_detailed_report(model_name: str, y_true, y_pred):
    """Print detailed classification report"""
    
    print(f"\n{'='*70}")
    print(f"CLASSIFICATION REPORT: {model_name}")
    print(f"{'='*70}")
    
    print("\n" + classification_report(y_true, y_pred, target_names=['Hop le (0)', 'Phishing (1)']))


def print_model_comparison_analysis(results: list, all_predictions: dict, y_test):
    """Print comparative analysis between models"""
    
    print("\n" + "=" * 90)
    print("                         PHAN TICH SO SANH CHI TIET")
    print("=" * 90)
    
    xgb = next(r for r in results if r['model'] == "XGBoost")
    rf = next(r for r in results if r['model'] == "Random Forest")
    lr = next(r for r in results if r['model'] == "Logistic Regression")
    
    print(f"""
+----------------------+------------+---------------+---------------------+
| Tieu chi             | XGBoost    | Random Forest | Logistic Regression |
+----------------------+------------+---------------+---------------------+
| Accuracy             | {xgb['accuracy']:>9.2%} | {rf['accuracy']:>12.2%} | {lr['accuracy']:>18.2%} |
| Precision            | {xgb['precision']:>9.2%} | {rf['precision']:>12.2%} | {lr['precision']:>18.2%} |
| Recall               | {xgb['recall']:>9.2%} | {rf['recall']:>12.2%} | {lr['recall']:>18.2%} |
| F1-Score             | {xgb['f1_score']:>9.4f} | {rf['f1_score']:>12.4f} | {lr['f1_score']:>18.4f} |
| Training Time        | {xgb['train_time']:>8.1f}s | {rf['train_time']:>11.1f}s | {lr['train_time']:>17.1f}s |
+----------------------+------------+---------------+---------------------+
""")
    
    # Calculate differences
    print("\nSO SANH CHENH LECH F1-Score:")
    print(f"  - XGBoost vs Random Forest:       {(xgb['f1_score'] - rf['f1_score'])*100:+.2f}% ({'XGBoost tot hon' if xgb['f1_score'] > rf['f1_score'] else 'Random Forest tot hon'})")
    print(f"  - XGBoost vs Logistic Regression: {(xgb['f1_score'] - lr['f1_score'])*100:+.2f}% ({'XGBoost tot hon' if xgb['f1_score'] > lr['f1_score'] else 'Logistic Regression tot hon'})")
    print(f"  - Random Forest vs Logistic:      {(rf['f1_score'] - lr['f1_score'])*100:+.2f}% ({'Random Forest tot hon' if rf['f1_score'] > lr['f1_score'] else 'Logistic Regression tot hon'})")


def print_conclusion(results: list):
    """Print final conclusion"""
    
    print("\n" + "=" * 90)
    print("                              KET LUAN")
    print("=" * 90)
    
    results_sorted = sorted(results, key=lambda x: x['f1_score'], reverse=True)
    
    print("\nXEP HANG THEO F1-Score:")
    medals = ["1.", "2.", "3."]
    for i, r in enumerate(results_sorted):
        star = ">>> " if i == 0 else "    "
        print(f"  {star}{medals[i]} {r['model']}: F1 = {r['f1_score']:.4f}")
    
    winner = results_sorted[0]
    
    print(f"""
+-----------------------------------------------------------------------+
|                         NHAN XET TONG KET                             |
+-----------------------------------------------------------------------+
| Mo hinh tot nhat: {winner['model']:<50} |
| F1-Score:         {winner['f1_score']:.4f}                                              |
+-----------------------------------------------------------------------+

LY DO CHON {winner['model'].upper()}:
""")
    
    if winner['model'] == "XGBoost":
        print("""  1. DO CHINH XAC CAO NHAT - Vuot troi so voi cac baseline
  2. GRADIENT BOOSTING - Moi cay hoc tu sai sot cua cay truoc
  3. REGULARIZATION - L1 + L2 giup tranh overfitting
  4. FEATURE IMPORTANCE - Co the giai thich duoc feature nao quan trong
  5. XU LY TOT DU LIEU KHONG CAN BANG - Phu hop voi bai toan phishing
""")
    elif winner['model'] == "Random Forest":
        print("""  1. DO CHINH XAC CAO - Ensemble cua nhieu cay quyet dinh
  2. IT OVERFITTING - Bagging giup giam variance
  3. TRAIN SONG SONG - Nhanh hon XGBoost
  4. KHONG CAN FEATURE SCALING - Don gian hoa preprocessing
""")
    else:
        print("""  1. DON GIAN VA NHANH - Train chi trong vai giay
  2. INTERPRETABLE - De giai thich ket qua
  3. XAC SUAT TRUC TIEP - Output chinh la probability
  4. BASELINE TOT - De so sanh voi cac model phuc tap hon
""")
    
    print("=" * 90)
    print("                         KET THUC SO SANH MO HINH")
    print("=" * 90)


def save_model(pipeline, model_name: str, threshold: float = 0.5):
    """Save trained model to models/ directory"""
    
    models_dir = project_root / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Convert name to filename
    filename_map = {
        "XGBoost": "xgboost.joblib",
        "Random Forest": "random_forest.joblib",
        "Logistic Regression": "logistic_regression.joblib"
    }
    
    filename = filename_map.get(model_name, f"{model_name.lower().replace(' ', '_')}.joblib")
    model_path = models_dir / filename
    
    # Save as package with threshold
    pkg = {
        "model": pipeline,
        "threshold": threshold,
        "suspicious_margin": 0.2,
        "model_name": model_name
    }
    
    dump(pkg, model_path)
    print(f"  → Da luu model: {model_path}")
    
    return model_path


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="So sanh 3 mo hinh phan loai phishing")
    parser.add_argument(
        "--save-models",
        action="store_true",
        help="Luu ca 3 model vao thu muc models/"
    )
    args = parser.parse_args()
    
    print("=" * 90)
    print("     SO SANH MO HINH: XGBoost vs Random Forest vs Logistic Regression")
    print("     Du an: Phat hien Email Lua dao (Phishing Detection)")
    print("=" * 90)
    
    # Print metrics explanation first
    print_metrics_explanation()
    
    # Find dataset
    data_dir = project_root / "data"
    incoming_dir = data_dir / "incoming"
    history_dir = data_dir / "history"
    
    # Try to find dataset
    data_path = None
    
    if incoming_dir.exists():
        for f in incoming_dir.glob("*.csv"):
            data_path = f
            break
    
    if data_path is None and history_dir.exists():
        for f in history_dir.glob("*.csv"):
            data_path = f
            break
    
    if data_path is None:
        print("ERROR: Khong tim thay dataset!")
        print("Vui long dat file CSV vao: data/incoming/")
        return
    
    print(f"\n{'='*70}")
    print("CHUAN BI DU LIEU")
    print(f"{'='*70}")
    print(f"Su dung dataset: {data_path.name}")
    
    # Prepare data
    df = prepare_data(data_path)
    
    print(f"\nTong so mau: {len(df):,}")
    print(f"\nPhan phoi label:")
    label_counts = df['label'].value_counts()
    print(f"  - Hop le (0):   {label_counts.get(0, 0):,} ({label_counts.get(0, 0)/len(df)*100:.1f}%)")
    print(f"  - Phishing (1): {label_counts.get(1, 0):,} ({label_counts.get(1, 0)/len(df)*100:.1f}%)")
    
    # Split data
    X = df[FEATURE_COLS]
    y = df['label']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    print(f"\nChia du lieu:")
    print(f"  - Training set: {len(X_train):,} mau (80%)")
    print(f"  - Testing set:  {len(X_test):,} mau (20%)")
    
    # Models to compare
    models = ["XGBoost", "Random Forest", "Logistic Regression"]
    
    results = []
    predictions = {}
    pipelines = {}  # Store pipelines for saving
    
    # Train and evaluate each model
    print(f"\n{'='*70}")
    print("BAT DAU HUAN LUYEN CAC MO HINH")
    print(f"{'='*70}")
    
    for model_name in models:
        print(f"\n{'='*50}")
        print(f"[TRAINING] {model_name}")
        print(f"{'='*50}")
        
        # Build pipeline
        pipeline = build_model_pipeline(model_name)
        
        # Train
        start_time = time.time()
        pipeline.fit(X_train, y_train)
        train_time = time.time() - start_time
        
        print(f"  Training hoan thanh trong {train_time:.2f} giay")
        
        # Predict
        y_pred = pipeline.predict(X_test)
        
        # Calculate metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted')
        rec = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        print(f"  Ket qua:")
        print(f"    - Accuracy:  {acc:.2%}")
        print(f"    - Precision: {prec:.2%}")
        print(f"    - Recall:    {rec:.2%}")
        print(f"    - F1-Score:  {f1:.4f}")
        
        results.append({
            'model': model_name,
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1_score': f1,
            'train_time': train_time,
            'pipeline': pipeline
        })
        predictions[model_name] = y_pred
        pipelines[model_name] = pipeline
    
    # Print comparison table
    print_comparison_table(results)
    
    # Print confusion matrices for each model
    for model_name in models:
        print_confusion_matrix_detail(model_name, y_test, predictions[model_name])
    
    # Print detailed classification reports
    for model_name in models:
        print_detailed_report(model_name, y_test, predictions[model_name])
    
    # Print comparative analysis
    print_model_comparison_analysis(results, predictions, y_test)
    
    # Print conclusion
    print_conclusion(results)
    
    # Save models if requested
    if args.save_models:
        print(f"\n{'='*70}")
        print("LUU CAC MO HINH")
        print(f"{'='*70}")
        for model_name, pipeline in pipelines.items():
            save_model(pipeline, model_name)
        print(f"\nDa luu {len(pipelines)} mo hinh vao thu muc models/")
        print("\nDe predict voi model khac, su dung:")
        print("  python -m src.predict --model models/random_forest.joblib --file email.txt")
        print("  python -m src.predict --model models/logistic_regression.joblib --file email.txt")


if __name__ == "__main__":
    main()
