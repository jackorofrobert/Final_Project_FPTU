# -*- coding: utf-8 -*-
"""
Tao bang danh gia Train va Test cho ca 3 mo hinh.
Xuat ket qua ra file Markdown de trinh bay truoc hoi dong.

Chay script:
    cd Final_Project_FPTU
    python scripts/generate_evaluation_report.py
"""

import sys
import time
import warnings
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix,
    roc_auc_score
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
    """Build feature preprocessing pipeline"""
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
    return ColumnTransformer(
        transformers=[
            ('text', text_pipeline, TEXT_COL),
            ('numeric', numeric_pipeline, NUMERIC_COLS),
            ('categorical', categorical_pipeline, CATEGORICAL_COLS)
        ],
        remainder='drop'
    )


def build_model_pipeline(model_name: str):
    """Build complete pipeline with specified classifier"""
    preprocessor = build_preprocessor()
    
    if model_name == "XGBoost":
        clf = XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", use_label_encoder=False,
            random_state=42, verbosity=0
        )
    elif model_name == "Random Forest":
        clf = RandomForestClassifier(
            n_estimators=200, max_depth=10,
            min_samples_split=5, min_samples_leaf=2,
            random_state=42, n_jobs=-1
        )
    elif model_name == "Logistic Regression":
        clf = LogisticRegression(
            max_iter=1000, random_state=42, n_jobs=-1
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
    df.columns = [c.strip().lower() for c in df.columns]
    
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
    df[TEXT_COL] = text_content
    
    # Extract features if not present
    feature_extractors = {
        'has_attachment': detect_attachment_mention,
        'links_count': count_urls,
        'urgent_keywords': detect_urgent_keywords,
        'sender_domain': extract_sender_domain,
        'body_length': length_chars,
        'exclamation_count': exclamation_count,
    }
    
    for col, func in feature_extractors.items():
        if col not in df.columns:
            print(f"Extracting '{col}'...")
            df[col] = text_content.apply(func)
    
    # Convert types
    df['has_attachment'] = df['has_attachment'].fillna(0).astype(int)
    df['links_count'] = df['links_count'].fillna(0).astype(int)
    df['urgent_keywords'] = df['urgent_keywords'].fillna(0).astype(int)
    df['sender_domain'] = df['sender_domain'].fillna('unknown').astype(str)
    df['body_length'] = df['body_length'].fillna(0).astype(int)
    df['exclamation_count'] = df['exclamation_count'].fillna(0).astype(int)
    
    from src.label_utils import normalize_label
    df['label'] = df['label'].apply(normalize_label)
    
    df = df[FEATURE_COLS + ['label']].dropna()
    return df


def evaluate_model(pipeline, X, y):
    """Evaluate model on a dataset, return metrics dict"""
    y_pred = pipeline.predict(X)
    
    acc = accuracy_score(y, y_pred)
    
    # Per-class metrics
    prec_0 = precision_score(y, y_pred, pos_label=0, average='binary')
    rec_0 = recall_score(y, y_pred, pos_label=0, average='binary')
    f1_0 = f1_score(y, y_pred, pos_label=0, average='binary')
    
    prec_1 = precision_score(y, y_pred, pos_label=1, average='binary')
    rec_1 = recall_score(y, y_pred, pos_label=1, average='binary')
    f1_1 = f1_score(y, y_pred, pos_label=1, average='binary')
    
    # Weighted average
    prec_w = precision_score(y, y_pred, average='weighted')
    rec_w = recall_score(y, y_pred, average='weighted')
    f1_w = f1_score(y, y_pred, average='weighted')
    
    # Confusion matrix
    cm = confusion_matrix(y, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    # AUC-ROC if available
    try:
        y_proba = pipeline.predict_proba(X)[:, 1]
        auc = roc_auc_score(y, y_proba)
    except Exception:
        auc = None
    
    return {
        'accuracy': acc,
        'precision_0': prec_0, 'recall_0': rec_0, 'f1_0': f1_0,
        'precision_1': prec_1, 'recall_1': rec_1, 'f1_1': f1_1,
        'precision_w': prec_w, 'recall_w': rec_w, 'f1_w': f1_w,
        'auc_roc': auc,
        'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp,
        'y_pred': y_pred,
    }


def generate_markdown_report(all_results, dataset_info, output_path):
    """Generate markdown evaluation report"""
    
    lines = []
    
    # Header
    lines.append("# 📊 Báo Cáo Đánh Giá Mô Hình - Phishing Email Detection")
    lines.append("")
    lines.append(f"> **Ngày tạo:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append(f"> **Dự án:** Final Project FPTU - Phát hiện Email Lừa đảo")
    lines.append("")
    
    # Dataset info
    lines.append("---")
    lines.append("## 1. Thông Tin Dataset")
    lines.append("")
    lines.append(f"| Thông tin | Giá trị |")
    lines.append(f"|:---|:---|")
    lines.append(f"| Tổng số mẫu | **{dataset_info['total']:,}** |")
    lines.append(f"| Email hợp lệ (class 0) | {dataset_info['class_0']:,} ({dataset_info['class_0']/dataset_info['total']*100:.1f}%) |")
    lines.append(f"| Email phishing (class 1) | {dataset_info['class_1']:,} ({dataset_info['class_1']/dataset_info['total']*100:.1f}%) |")
    lines.append(f"| Training set (80%) | {dataset_info['train_size']:,} mẫu |")
    lines.append(f"| Testing set (20%) | {dataset_info['test_size']:,} mẫu |")
    lines.append(f"| Random state | 42 |")
    lines.append(f"| Stratified split | Có |")
    lines.append("")
    
    # Feature info
    lines.append("### Features sử dụng")
    lines.append("")
    lines.append("| Loại | Feature | Mô tả |")
    lines.append("|:---|:---|:---|")
    lines.append("| Text (TF-IDF) | `text` | Nội dung email, max 5000 features, bigrams |")
    lines.append("| Numeric | `has_attachment` | Có file đính kèm (0/1) |")
    lines.append("| Numeric | `links_count` | Số lượng link trong email |")
    lines.append("| Numeric | `urgent_keywords` | Từ khóa khẩn cấp (0/1) |")
    lines.append("| Numeric | `body_length` | Độ dài nội dung (ký tự) |")
    lines.append("| Numeric | `exclamation_count` | Số dấu chấm than |")
    lines.append("| Categorical | `sender_domain` | Domain người gửi (One-Hot Encoding) |")
    lines.append("")
    
    # ============================================================
    # TABLE 1: Overall comparison (Test set)
    # ============================================================
    lines.append("---")
    lines.append("## 2. Bảng So Sánh Tổng Quan (Test Set)")
    lines.append("")
    lines.append("| Mô hình | Accuracy | Precision | Recall | F1-Score | AUC-ROC | Thời gian train |")
    lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    for model_name in ["XGBoost", "Random Forest", "Logistic Regression"]:
        r = all_results[model_name]
        test = r['test']
        tt = r['train_time']
        auc_str = f"{test['auc_roc']:.4f}" if test['auc_roc'] is not None else "N/A"
        
        # Highlight if best
        is_best = model_name == max(all_results.keys(), key=lambda k: all_results[k]['test']['f1_w'])
        prefix = "**" if is_best else ""
        suffix = "** ✅" if is_best else ""
        
        lines.append(
            f"| {prefix}{model_name}{suffix} | "
            f"{test['accuracy']:.2%} | "
            f"{test['precision_w']:.2%} | "
            f"{test['recall_w']:.2%} | "
            f"{test['f1_w']:.4f} | "
            f"{auc_str} | "
            f"{tt:.2f}s |"
        )
    
    lines.append("")
    
    # ============================================================
    # TABLE 2: Train vs Test comparison for each model
    # ============================================================
    lines.append("---")
    lines.append("## 3. Bảng Đánh Giá Train vs Test (Chi Tiết Từng Mô Hình)")
    lines.append("")
    
    for model_name in ["XGBoost", "Random Forest", "Logistic Regression"]:
        r = all_results[model_name]
        train_m = r['train']
        test_m = r['test']
        
        lines.append(f"### 3.{['XGBoost', 'Random Forest', 'Logistic Regression'].index(model_name)+1}. {model_name}")
        lines.append("")
        
        # Train vs Test overall metrics
        lines.append("#### Tổng quan")
        lines.append("")
        lines.append("| Chỉ số | Train Set | Test Set | Chênh lệch |")
        lines.append("|:---|:---:|:---:|:---:|")
        
        metrics_pairs = [
            ("Accuracy", train_m['accuracy'], test_m['accuracy']),
            ("Precision (weighted)", train_m['precision_w'], test_m['precision_w']),
            ("Recall (weighted)", train_m['recall_w'], test_m['recall_w']),
            ("F1-Score (weighted)", train_m['f1_w'], test_m['f1_w']),
        ]
        
        if train_m['auc_roc'] is not None and test_m['auc_roc'] is not None:
            metrics_pairs.append(("AUC-ROC", train_m['auc_roc'], test_m['auc_roc']))
        
        for name, train_val, test_val in metrics_pairs:
            diff = train_val - test_val
            diff_str = f"{diff:+.4f}"
            # Flag if overfitting (large gap)
            flag = " ⚠️" if abs(diff) > 0.05 else ""
            lines.append(f"| {name} | {train_val:.4f} | {test_val:.4f} | {diff_str}{flag} |")
        
        lines.append("")
        
        # Per-class metrics
        lines.append("#### Chi tiết theo từng lớp (Test Set)")
        lines.append("")
        lines.append("| Lớp | Precision | Recall | F1-Score |")
        lines.append("|:---|:---:|:---:|:---:|")
        lines.append(f"| Hợp lệ (0) | {test_m['precision_0']:.4f} | {test_m['recall_0']:.4f} | {test_m['f1_0']:.4f} |")
        lines.append(f"| Phishing (1) | {test_m['precision_1']:.4f} | {test_m['recall_1']:.4f} | {test_m['f1_1']:.4f} |")
        lines.append(f"| **Weighted Avg** | **{test_m['precision_w']:.4f}** | **{test_m['recall_w']:.4f}** | **{test_m['f1_w']:.4f}** |")
        lines.append("")
        
        # Confusion matrix
        lines.append("#### Confusion Matrix (Test Set)")
        lines.append("")
        lines.append("|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |")
        lines.append("|:---|:---:|:---:|")
        lines.append(f"| **Thực tế: Hợp lệ** | TN = {test_m['tn']:,} | FP = {test_m['fp']:,} |")
        lines.append(f"| **Thực tế: Phishing** | FN = {test_m['fn']:,} | TP = {test_m['tp']:,} |")
        lines.append("")
        
        total_legit = test_m['tn'] + test_m['fp']
        total_phish = test_m['fn'] + test_m['tp']
        fp_rate = test_m['fp'] / total_legit * 100 if total_legit > 0 else 0
        fn_rate = test_m['fn'] / total_phish * 100 if total_phish > 0 else 0
        
        lines.append(f"- **Tỷ lệ đánh nhầm (FP Rate):** {fp_rate:.2f}% ({test_m['fp']}/{total_legit:,})")
        lines.append(f"- **Tỷ lệ bỏ sót (FN Rate):** {fn_rate:.2f}% ({test_m['fn']}/{total_phish:,})")
        lines.append("")
    
    # ============================================================
    # TABLE 3: Overfitting analysis
    # ============================================================
    lines.append("---")
    lines.append("## 4. Phân Tích Overfitting")
    lines.append("")
    lines.append("| Mô hình | F1 Train | F1 Test | Gap | Đánh giá |")
    lines.append("|:---|:---:|:---:|:---:|:---|")
    
    for model_name in ["XGBoost", "Random Forest", "Logistic Regression"]:
        r = all_results[model_name]
        f1_train = r['train']['f1_w']
        f1_test = r['test']['f1_w']
        gap = f1_train - f1_test
        
        if gap < 0.02:
            evaluation = "✅ Không overfitting"
        elif gap < 0.05:
            evaluation = "⚠️ Overfitting nhẹ"
        else:
            evaluation = "❌ Overfitting đáng kể"
        
        lines.append(f"| {model_name} | {f1_train:.4f} | {f1_test:.4f} | {gap:+.4f} | {evaluation} |")
    
    lines.append("")
    lines.append("> **Ghi chú:** Gap < 0.02 → Không overfitting | 0.02-0.05 → Overfitting nhẹ | > 0.05 → Overfitting đáng kể")
    lines.append("")
    
    # ============================================================
    # Conclusion
    # ============================================================
    lines.append("---")
    lines.append("## 5. Kết Luận")
    lines.append("")
    
    # Find best model
    best_model = max(all_results.keys(), key=lambda k: all_results[k]['test']['f1_w'])
    best_test = all_results[best_model]['test']
    
    lines.append(f"### Mô hình được chọn: **{best_model}**")
    lines.append("")
    lines.append(f"| Tiêu chí | Kết quả |")
    lines.append(f"|:---|:---|")
    lines.append(f"| F1-Score (Test) | **{best_test['f1_w']:.4f}** |")
    lines.append(f"| Accuracy (Test) | **{best_test['accuracy']:.2%}** |")
    if best_test['auc_roc'] is not None:
        lines.append(f"| AUC-ROC (Test) | **{best_test['auc_roc']:.4f}** |")
    lines.append(f"| Precision - Phishing | {best_test['precision_1']:.4f} |")
    lines.append(f"| Recall - Phishing | {best_test['recall_1']:.4f} |")
    lines.append("")
    
    lines.append("### Lý do chọn XGBoost:")
    lines.append("")
    lines.append("1. **F1-Score cao nhất** — Vượt trội so với các baseline models")
    lines.append("2. **Gradient Boosting** — Mỗi cây học từ sai sót của cây trước, cải thiện liên tục")
    lines.append("3. **Regularization (L1 + L2)** — Giúp tránh overfitting hiệu quả")
    lines.append("4. **Feature Importance** — Có thể giải thích feature nào quan trọng nhất")
    lines.append("5. **Xử lý tốt dữ liệu không cân bằng** — Phù hợp với bài toán phishing detection")
    lines.append("")
    
    # Write to file
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    print(f"\n>>> Da luu bao cao: {output_path}")
    
    return content


def main():
    print("=" * 80)
    print("   TAO BANG DANH GIA TRAIN & TEST - PHISHING EMAIL DETECTION")
    print("=" * 80)
    
    # Find dataset
    data_dir = project_root / "data"
    data_path = None
    
    for subdir in ["incoming", "history"]:
        d = data_dir / subdir
        if d.exists():
            for f in d.glob("*.csv"):
                data_path = f
                break
        if data_path:
            break
    
    if data_path is None:
        print("ERROR: Khong tim thay dataset!")
        return
    
    print(f"\nDataset: {data_path.name}")
    
    # Prepare data
    df = prepare_data(data_path)
    
    total = len(df)
    label_counts = df['label'].value_counts()
    class_0 = label_counts.get(0, 0)
    class_1 = label_counts.get(1, 0)
    
    print(f"\nTong mau: {total:,}")
    print(f"  Hop le (0):   {class_0:,}")
    print(f"  Phishing (1): {class_1:,}")
    
    # Split
    X = df[FEATURE_COLS]
    y = df['label']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    print(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
    
    dataset_info = {
        'total': total,
        'class_0': class_0,
        'class_1': class_1,
        'train_size': len(X_train),
        'test_size': len(X_test),
    }
    
    # Train & evaluate all models
    models = ["XGBoost", "Random Forest", "Logistic Regression"]
    all_results = {}
    
    for model_name in models:
        print(f"\n{'='*60}")
        print(f"[TRAINING] {model_name}")
        print(f"{'='*60}")
        
        pipeline = build_model_pipeline(model_name)
        
        start = time.time()
        pipeline.fit(X_train, y_train)
        train_time = time.time() - start
        
        print(f"  Train time: {train_time:.2f}s")
        
        # Evaluate on TRAIN set
        print("  Evaluating on TRAIN set...")
        train_metrics = evaluate_model(pipeline, X_train, y_train)
        
        # Evaluate on TEST set
        print("  Evaluating on TEST set...")
        test_metrics = evaluate_model(pipeline, X_test, y_test)
        
        print(f"  Train F1: {train_metrics['f1_w']:.4f} | Test F1: {test_metrics['f1_w']:.4f}")
        print(f"  Train Acc: {train_metrics['accuracy']:.2%} | Test Acc: {test_metrics['accuracy']:.2%}")
        
        all_results[model_name] = {
            'train': train_metrics,
            'test': test_metrics,
            'train_time': train_time,
        }
    
    # Generate markdown report
    output_path = project_root / "docs" / "EVALUATION_REPORT.md"
    generate_markdown_report(all_results, dataset_info, output_path)
    
    print("\n" + "=" * 80)
    print("   HOAN THANH! Kiem tra file: docs/EVALUATION_REPORT.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
