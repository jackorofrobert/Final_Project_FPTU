# 📊 Báo Cáo Đánh Giá Mô Hình - Phishing Email Detection

> **Ngày tạo:** 07/03/2026 10:58
> **Dự án:** Final Project FPTU - Phát hiện Email Lừa đảo

---
## 1. Thông Tin Dataset

| Thông tin | Giá trị |
|:---|:---|
| Tổng số mẫu | **212,085** |
| Email hợp lệ (class 0) | 113,096 (53.3%) |
| Email phishing (class 1) | 98,989 (46.7%) |
| Training set (80%) | 169,668 mẫu |
| Testing set (20%) | 42,417 mẫu |
| Random state | 42 |
| Stratified split | Có |

### Features sử dụng

| Loại | Feature | Mô tả |
|:---|:---|:---|
| Text (TF-IDF) | `text` | Nội dung email, max 5000 features, bigrams |
| Numeric | `has_attachment` | Có file đính kèm (0/1) |
| Numeric | `links_count` | Số lượng link trong email |
| Numeric | `urgent_keywords` | Từ khóa khẩn cấp (0/1) |
| Numeric | `body_length` | Độ dài nội dung (ký tự) |
| Numeric | `exclamation_count` | Số dấu chấm than |
| Categorical | `sender_domain` | Domain người gửi (One-Hot Encoding) |

---
## 2. Bảng So Sánh Tổng Quan (Test Set)

| Mô hình | Accuracy | Precision | Recall | F1-Score | AUC-ROC | Thời gian train |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| XGBoost | 95.82% | 95.90% | 95.82% | 0.9582 | 0.9930 | 427.55s |
| Random Forest | 89.66% | 90.24% | 89.66% | 0.8967 | 0.9716 | 258.77s |
| **Logistic Regression** ✅ | 97.10% | 97.11% | 97.10% | 0.9710 | 0.9960 | 418.59s |

---
## 3. Bảng Đánh Giá Train vs Test (Chi Tiết Từng Mô Hình)

### 3.1. XGBoost

#### Tổng quan

| Chỉ số | Train Set | Test Set | Chênh lệch |
|:---|:---:|:---:|:---:|
| Accuracy | 0.9643 | 0.9582 | +0.0061 |
| Precision (weighted) | 0.9650 | 0.9590 | +0.0060 |
| Recall (weighted) | 0.9643 | 0.9582 | +0.0061 |
| F1-Score (weighted) | 0.9643 | 0.9582 | +0.0061 |
| AUC-ROC | 0.9945 | 0.9930 | +0.0015 |

#### Chi tiết theo từng lớp (Test Set)

| Lớp | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|
| Hợp lệ (0) | 0.9782 | 0.9426 | 0.9601 |
| Phishing (1) | 0.9370 | 0.9760 | 0.9561 |
| **Weighted Avg** | **0.9590** | **0.9582** | **0.9582** |

#### Confusion Matrix (Test Set)

|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |
|:---|:---:|:---:|
| **Thực tế: Hợp lệ** | TN = 21,320 | FP = 1,299 |
| **Thực tế: Phishing** | FN = 475 | TP = 19,323 |

- **Tỷ lệ đánh nhầm (FP Rate):** 5.74% (1299/22,619)
- **Tỷ lệ bỏ sót (FN Rate):** 2.40% (475/19,798)

### 3.2. Random Forest

#### Tổng quan

| Chỉ số | Train Set | Test Set | Chênh lệch |
|:---|:---:|:---:|:---:|
| Accuracy | 0.8990 | 0.8966 | +0.0024 |
| Precision (weighted) | 0.9048 | 0.9024 | +0.0024 |
| Recall (weighted) | 0.8990 | 0.8966 | +0.0024 |
| F1-Score (weighted) | 0.8991 | 0.8967 | +0.0024 |
| AUC-ROC | 0.9733 | 0.9716 | +0.0016 |

#### Chi tiết theo từng lớp (Test Set)

| Lớp | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|
| Hợp lệ (0) | 0.9503 | 0.8507 | 0.8977 |
| Phishing (1) | 0.8477 | 0.9491 | 0.8955 |
| **Weighted Avg** | **0.9024** | **0.8966** | **0.8967** |

#### Confusion Matrix (Test Set)

|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |
|:---|:---:|:---:|
| **Thực tế: Hợp lệ** | TN = 19,242 | FP = 3,377 |
| **Thực tế: Phishing** | FN = 1,007 | TP = 18,791 |

- **Tỷ lệ đánh nhầm (FP Rate):** 14.93% (3377/22,619)
- **Tỷ lệ bỏ sót (FN Rate):** 5.09% (1007/19,798)

### 3.3. Logistic Regression

#### Tổng quan

| Chỉ số | Train Set | Test Set | Chênh lệch |
|:---|:---:|:---:|:---:|
| Accuracy | 0.9756 | 0.9710 | +0.0046 |
| Precision (weighted) | 0.9756 | 0.9711 | +0.0046 |
| Recall (weighted) | 0.9756 | 0.9710 | +0.0046 |
| F1-Score (weighted) | 0.9756 | 0.9710 | +0.0046 |
| AUC-ROC | 0.9969 | 0.9960 | +0.0008 |

#### Chi tiết theo từng lớp (Test Set)

| Lớp | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|
| Hợp lệ (0) | 0.9775 | 0.9679 | 0.9727 |
| Phishing (1) | 0.9637 | 0.9745 | 0.9691 |
| **Weighted Avg** | **0.9711** | **0.9710** | **0.9710** |

#### Confusion Matrix (Test Set)

|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |
|:---|:---:|:---:|
| **Thực tế: Hợp lệ** | TN = 21,893 | FP = 726 |
| **Thực tế: Phishing** | FN = 504 | TP = 19,294 |

- **Tỷ lệ đánh nhầm (FP Rate):** 3.21% (726/22,619)
- **Tỷ lệ bỏ sót (FN Rate):** 2.55% (504/19,798)

---
## 4. Phân Tích Overfitting

| Mô hình | F1 Train | F1 Test | Gap | Đánh giá |
|:---|:---:|:---:|:---:|:---|
| XGBoost | 0.9643 | 0.9582 | +0.0061 | ✅ Không overfitting |
| Random Forest | 0.8991 | 0.8967 | +0.0024 | ✅ Không overfitting |
| Logistic Regression | 0.9756 | 0.9710 | +0.0046 | ✅ Không overfitting |

> **Ghi chú:** Gap < 0.02 → Không overfitting | 0.02-0.05 → Overfitting nhẹ | > 0.05 → Overfitting đáng kể

---
## 5. Kết Luận

### Xếp hạng mô hình theo F1-Score (Test Set)

| Hạng | Mô hình | F1-Score | Accuracy | AUC-ROC |
|:---:|:---|:---:|:---:|:---:|
| 🥇 1 | **Logistic Regression** | **0.9710** | **97.10%** | **0.9960** |
| 🥈 2 | XGBoost | 0.9582 | 95.82% | 0.9930 |
| 🥉 3 | Random Forest | 0.8967 | 89.66% | 0.9716 |

### Mô hình sử dụng trong dự án: **XGBoost**

Mặc dù Logistic Regression đạt F1-Score cao nhất trên tập test, dự án vẫn sử dụng **XGBoost** vì các lý do thực tiễn sau:

1. **Ensemble Scoring Formula** — XGBoost cung cấp `predict_proba` chất lượng cao, phù hợp với công thức tính điểm ensemble (70% model + 12% urgent + 10.5% links + 7.5% domain)
2. **Feature Importance** — XGBoost cho phép phân tích feature nào đóng góp nhiều nhất vào việc phát hiện phishing, giúp giải thích kết quả cho người dùng
3. **Khả năng mở rộng** — Gradient Boosting xử lý tốt khi thêm dataset mới (Dataset Memory), mỗi cây học từ sai sót của cây trước
4. **Regularization (L1 + L2)** — Giúp tránh overfitting khi dataset tăng theo thời gian
5. **Xử lý tốt dữ liệu không cân bằng** — Phù hợp với bài toán phishing detection trong thực tế

> **Lưu ý:** Logistic Regression đạt kết quả xuất sắc (F1=0.9710) nhờ TF-IDF features hiệu quả trên text data. Tuy nhiên, XGBoost linh hoạt hơn khi cần tích hợp thêm features mới và phù hợp hơn với kiến trúc scoring của hệ thống.
