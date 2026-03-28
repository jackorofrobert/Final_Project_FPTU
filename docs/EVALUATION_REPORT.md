# 📊 Báo Cáo Đánh Giá Mô Hình - Phishing Email Detection

> **Ngày tạo:** 07/03/2026 | **Cập nhật:** 13/03/2026 *(chạy lại)*  
> **Dự án:** Final Project FPTU - Phát hiện Email Lừa đảo

---
## 1. Thông Tin Dataset

| Thông tin | Giá trị |
|:---|:---|
| File | `data/incoming/Balanced_Dataset.csv` |
| Tổng số mẫu (sau filter) | **198,450** |
| Email hợp lệ (class 0) | ~99,225 (50%) |
| Email phishing (class 1) | ~99,225 (50%) |
| Training set (80%) | **158,760** mẫu |
| Testing set (20%) | **39,690** mẫu |
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

| Mô hình | Accuracy | Precision | Recall | F1-Score | AUC-ROC | Train time |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| XGBoost ⭐ *(production)* | 95.82% | 95.88% | 95.82% | 0.9581 | 0.9924 | 428.59s |
| Random Forest | 87.42% | 88.70% | 87.42% | 0.8731 | 0.9688 | 337.61s |
| **Logistic Regression** 🥇 | **96.93%** | **96.93%** | **96.93%** | **0.9693** | **0.9953** | 498.67s |

---
## 3. Bảng Đánh Giá Train vs Test (Chi Tiết Từng Mô Hình)

### 3.1. XGBoost

#### Tổng quan

| Chỉ số | Train Set | Test Set | Chênh lệch |
|:---|:---:|:---:|:---:|
| Accuracy | 0.9643 | 0.9582 | +0.0061 |
| Precision (weighted) | 0.9650 | 0.9588 | +0.0062 |
| Recall (weighted) | 0.9643 | 0.9582 | +0.0061 |
| F1-Score (weighted) | 0.9643 | 0.9581 | +0.0062 |
| AUC-ROC | 0.9946 | 0.9924 | +0.0022 |

#### Chi tiết theo từng lớp (Test Set)

| Lớp | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|
| Hợp lệ (0) | 0.9767 | 0.9387 | 0.9573 |
| Phishing (1) | 0.9410 | 0.9776 | 0.9590 |
| **Weighted Avg** | **0.9588** | **0.9582** | **0.9581** |

#### Confusion Matrix (Test Set)

|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |
|:---|:---:|:---:|
| **Thực tế: Hợp lệ** | TN = 18,628 | FP = 1,217 |
| **Thực tế: Phishing** | FN = 444 | TP = 19,401 |

- **Tỷ lệ đánh nhầm (FP Rate):** 6.13% (1,217/19,845)
- **Tỷ lệ bỏ sót (FN Rate):** 2.24% (444/19,845)

### 3.2. Random Forest

#### Tổng quan

| Chỉ số | Train Set | Test Set | Chênh lệch |
|:---|:---:|:---:|:---:|
| Accuracy | 0.8753 | 0.8742 | +0.0011 |
| Precision (weighted) | 0.8897 | 0.8870 | +0.0027 |
| Recall (weighted) | 0.8753 | 0.8742 | +0.0011 |
| F1-Score (weighted) | 0.8741 | 0.8731 | +0.0010 |
| AUC-ROC | 0.9717 | 0.9688 | +0.0029 |

#### Chi tiết theo từng lớp (Test Set)

| Lớp | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|
| Hợp lệ (0) | 0.9575 | 0.7832 | 0.8616 |
| Phishing (1) | 0.8166 | 0.9652 | 0.8847 |
| **Weighted Avg** | **0.8870** | **0.8742** | **0.8731** |

#### Confusion Matrix (Test Set)

|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |
|:---|:---:|:---:|
| **Thực tế: Hợp lệ** | TN = 15,542 | FP = 4,303 |
| **Thực tế: Phishing** | FN = 690 | TP = 19,155 |

- **Tỷ lệ đánh nhầm (FP Rate):** 21.68% (4,303/19,845)
- **Tỷ lệ bỏ sót (FN Rate):** 3.48% (690/19,845)

### 3.3. Logistic Regression

#### Tổng quan

| Chỉ số | Train Set | Test Set | Chênh lệch |
|:---|:---:|:---:|:---:|
| Accuracy | 0.9753 | 0.9693 | +0.0060 |
| Precision (weighted) | 0.9754 | 0.9693 | +0.0061 |
| Recall (weighted) | 0.9753 | 0.9693 | +0.0060 |
| F1-Score (weighted) | 0.9753 | 0.9693 | +0.0060 |
| AUC-ROC | 0.9969 | 0.9953 | +0.0016 |

#### Chi tiết theo từng lớp (Test Set)

| Lớp | Precision | Recall | F1-Score |
|:---|:---:|:---:|:---:|
| Hợp lệ (0) | 0.9734 | 0.9650 | 0.9692 |
| Phishing (1) | 0.9653 | 0.9736 | 0.9694 |
| **Weighted Avg** | **0.9693** | **0.9693** | **0.9693** |

#### Confusion Matrix (Test Set)

|  | Dự đoán: Hợp lệ | Dự đoán: Phishing |
|:---|:---:|:---:|
| **Thực tế: Hợp lệ** | TN = 19,151 | FP = 694 |
| **Thực tế: Phishing** | FN = 524 | TP = 19,321 |

- **Tỷ lệ đánh nhầm (FP Rate):** 3.50% (694/19,845)
- **Tỷ lệ bỏ sót (FN Rate):** 2.64% (524/19,845)

---
## 4. Phân Tích Overfitting

| Mô hình | F1 Train | F1 Test | Gap | Đánh giá |
|:---|:---:|:---:|:---:|:---|
| XGBoost | 0.9643 | 0.9581 | +0.0062 | ✅ Không overfitting |
| Random Forest | 0.8741 | 0.8731 | +0.0010 | ✅ Không overfitting |
| Logistic Regression | 0.9753 | 0.9693 | +0.0060 | ✅ Không overfitting |

> **Ghi chú:** Gap < 0.02 → Không overfitting | 0.02–0.05 → Overfitting nhẹ | > 0.05 → Overfitting đáng kể

---
## 5. Kết Luận

### Xếp hạng mô hình theo F1-Score (Test Set)

| Hạng | Mô hình | F1-Score | Accuracy | AUC-ROC |
|:---:|:---|:---:|:---:|:---:|
| 🥇 1 | **Logistic Regression** | **0.9693** | **96.93%** | **0.9953** |
| 🥈 2 | XGBoost | 0.9581 | 95.82% | 0.9924 |
| 🥉 3 | Random Forest | 0.8731 | 87.42% | 0.9688 |

### Mô hình sử dụng trong dự án: **XGBoost** ⭐

Mặc dù Logistic Regression đạt F1-Score cao nhất trên tập test, dự án vẫn sử dụng **XGBoost** vì các lý do thực tiễn sau:

1. **Ensemble Scoring** — XGBoost cho `predict_proba` chất lượng cao, là input cho Ensemble Formula (55% model + 20% urgent + 15% links + 10% domain)
2. **Feature Importance** — Có thể phân tích feature nào quan trọng nhất, giúp giải thích kết quả cho giáo viên/người dùng
3. **Khả năng mở rộng** — Gradient Boosting học tốt từ sai sót cây trước, phù hợp khi thêm dataset mới theo thời gian
4. **Regularization (L1 + L2)** — Tránh overfitting khi dataset tăng
5. **Xử lý dữ liệu không cân bằng** — Phù hợp thực tế phishing detection

> **Lưu ý:** Logistic Regression đạt F1=0.9693 nhờ TF-IDF hiệu quả trên text. Tuy nhiên XGBoost linh hoạt hơn khi tích hợp thêm features mới và phù hợp kiến trúc scoring hệ thống.

---
## 6. Công Thức Ensemble Scoring (Production)

XGBoost output chỉ chiếm **55%** điểm cuối. Hệ thống dùng Ensemble Scoring để bổ sung tín hiệu phishing hiện đại:

```
Ensemble Score = Model_proba × 55%
              + Urgent_keywords × 20%
              + Links_risk × 15%
              + Domain_risk × 10%
```

| Component | Mức rủi ro | Giá trị |
|:---|:---|:---:|
| Links — Trusted domain | An toàn | 0.0 |
| Links — Bình thường | Thấp | 0.1 |
| Links — Shortener (bit.ly...) | Cao | 0.6 |
| Links — Suspicious URL pattern | Rất cao | 0.7 |
| Links — IP-based URL | Nguy hiểm | 0.9 |
| Domain — Trong whitelist | An toàn | 0.0 |
| Domain — Unknown / không whitelist | Nghi ngờ | 0.5 |

**Ngưỡng phân loại:**

| Ensemble Score | Kết quả |
|:---:|:---|
| < 0.50 | ✅ LEGITIMATE |
| 0.50 – 0.70 | ⚡ SUSPICIOUS |
| ≥ 0.70 | 🚨 PHISHING |

---
## 7. Phân Tích Chuyên Sâu (In-depth Analysis)

> **Mục tiêu:** Hiểu rõ tại sao mô hình đưa ra quyết định và các trường hợp mô hình còn gặp khó khăn.

### 7.1. Tầm quan trọng của Features (Feature Importance)

Dưới đây là các đặc trưng (features) đóng góp nhiều nhất vào khả năng dự đoán của mô hình **XGBoost**:

| Top Features | Trọng số (Weight) | Ý nghĩa kỹ thuật |
|:---|:---:|:---|
| `links_count` | **0.0401** | Số lượng link là đặc trưng quan trọng nhất để nhận diện spam/phishing. |
| `urgent_keywords` | **0.0253** | Sự xuất hiện của các từ khóa "khẩn cấp" có trọng số rất cao. |
| `body_length` | **0.0156** | Độ dài nội dung giúp phân biệt mail thông báo ngắn với mail phishing dài. |
| `click` (text) | 0.0122 | Từ khóa hành động dụ dỗ người dùng click. |
| `account` (text) | 0.0115 | Liên quan đến việc thu thập thông tin tài khoản. |
| `has_attachment` | 0.0055 | Sự hiện diện của file đính kèm (invoice, document). |

### 7.2. Phân tích lỗi (Error Analysis)

Hệ thống vẫn gặp một số sai số nhỏ (tổng cộng ~1,700 mẫu trên 40,000 mẫu test). Phân tích các trường hợp này giúp cải thiện hệ thống:

#### A. False Positives (Đánh nhầm mail hợp lệ thành Phishing)
- **Tỷ lệ:** ~6.13%
- **Nguyên nhân chủ yếu:** 
    - Các mail quảng cáo (Marketing) sử dụng ngôn ngữ khẩn cấp như *"OFF 15% - 1 WEEK ONLY!"* hoặc *"Claim your reward now!"*.
    - Các bản tin (Newsletter) chứa quá nhiều link (Social media, unsubscribe, article links).
- **Giải pháp:** Sử dụng **Ensemble Scoring** (thành phần Domain Risk) để giảm điểm rủi ro nếu domain gửi đến từ các nguồn uy tín trong Whitelist.

#### B. False Negatives (Bỏ sót mail Phishing)
- **Tỷ lệ:** **Cực thấp (2.24%)**
- **Nguyên nhân chủ yếu:** 
    - Các mail phishing "tinh vi" (Spear Phishing) không dùng từ khóa khẩn cấp, chỉ có 1 câu chào hỏi đơn giản và 1 link duy nhất.
    - Mail phishing được trình bày dưới dạng ảnh hoàn toàn (không có text để AI phân tích).
- **Giải pháp:** Cải thiện logic trích xuất text từ HTML và tăng cường phân tích sâu từng URL (Link Risk).

### 7.3. Sức mạnh của TF-IDF Bi-grams
Nhờ sử dụng **ngram_range=(1, 2)**, mô hình không chỉ hiểu các từ đơn lẻ mà còn hiểu được các cụm từ nguy hiểm:
- *"bank account"*
- *"secure login"*
- *"verify your"*
- *"unauthorized access"*

Việc kết hợp **5000 đặc trưng ngôn ngữ** này giúp XGBoost đạt độ chính xác thực tế vượt trội so với các mô hình chỉ dựa trên đếm từ đơn giản.

---
> 📄 Xem toàn bộ pipeline: [PIPELINE_WORKFLOW.md](PIPELINE_WORKFLOW.md)
