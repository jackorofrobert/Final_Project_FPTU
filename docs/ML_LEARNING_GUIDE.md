# Hướng Dẫn Học Machine Learning (ML)

> **📚 Tài liệu dành cho nhóm** - Giúp hiểu rõ các khái niệm cơ bản về Machine Learning và cách áp dụng vào bài toán phát hiện email lừa đảo.

---

## Mục Lục

1. [Machine Learning là gì?](#1-machine-learning-là-gì)
2. [Các loại Machine Learning](#2-các-loại-machine-learning)
3. [Quy trình xây dựng mô hình ML](#3-quy-trình-xây-dựng-mô-hình-ml)
4. [Decision Tree (Cây quyết định)](#4-decision-tree-cây-quyết-định)
5. [Ensemble Methods (Phương pháp kết hợp)](#5-ensemble-methods-phương-pháp-kết-hợp)
6. [XGBoost - Thuật toán trong dự án](#6-xgboost---thuật-toán-trong-dự-án)
7. [Các chỉ số đánh giá mô hình](#7-các-chỉ-số-đánh-giá-mô-hình)
8. [Tóm tắt và Lời khuyên](#8-tóm-tắt-và-lời-khuyên)

---

## 1. Machine Learning là gì?

### 1.1 Định nghĩa

**Machine Learning (Học máy)** là một nhánh của Trí tuệ nhân tạo (AI) cho phép máy tính **học từ dữ liệu** mà không cần được lập trình cụ thể từng bước.

> 💡 **Ví dụ đơn giản:**  
> Thay vì viết 1000 luật để phân biệt email lừa đảo, ta cho máy "học" từ 200.000 email đã được gán nhãn. Máy sẽ tự tìm ra các mẫu (patterns) để phân loại.

### 1.2 So sánh với lập trình truyền thống

| Lập trình truyền thống | Machine Learning |
|------------------------|------------------|
| Lập trình viên viết luật cụ thể | Máy tự học luật từ dữ liệu |
| `if "urgent" in email: spam` | Học từ 1000 email spam để tìm patterns |
| Khó mở rộng | Dễ mở rộng với dữ liệu mới |
| Cần hiểu rõ bài toán | Cần dữ liệu chất lượng |

### 1.3 Ứng dụng thực tế

- **Email spam filter**: Gmail, Outlook
- **Gợi ý sản phẩm**: Shopee, Netflix, Spotify
- **Nhận diện khuôn mặt**: Điện thoại, Facebook
- **Xe tự lái**: Tesla, Waymo
- **Chatbot**: ChatGPT, Google Assistant
- **Phát hiện gian lận**: Ngân hàng, Credit card

---

## 2. Các loại Machine Learning

### 2.1 Supervised Learning (Học có giám sát) ⭐

> **Đây là loại ML được sử dụng trong dự án của chúng ta**

**Đặc điểm:**
- Dữ liệu training có **nhãn (label)** sẵn
- Mô hình học ánh xạ từ input → output
- Đánh giá được kết quả chính xác hay sai

**Ví dụ trong dự án:**
```
Input: "Verify your account immediately or it will be suspended"
Label: 1 (Phishing/Lừa đảo)

Input: "Meeting tomorrow at 3pm, please confirm attendance"  
Label: 0 (Legitimate/Hợp lệ)
```

**Các bài toán Supervised Learning:**

| Loại | Mô tả | Ví dụ |
|------|-------|-------|
| **Classification** | Phân loại vào các nhóm rời rạc | Email lừa đảo hay hợp lệ? ✅ (dự án của ta) |
| **Regression** | Dự đoán giá trị liên tục | Giá nhà là bao nhiêu? |

### 2.2 Unsupervised Learning (Học không giám sát)

**Đặc điểm:**
- Dữ liệu **không có nhãn**
- Mô hình tự tìm cấu trúc ẩn trong dữ liệu

**Ví dụ:**
- **Clustering**: Nhóm khách hàng tương tự nhau
- **Anomaly Detection**: Phát hiện giao dịch bất thường

### 2.3 Reinforcement Learning (Học tăng cường)

**Đặc điểm:**
- Agent (tác tử) học thông qua tương tác với môi trường
- Nhận phần thưởng (reward) hoặc hình phạt (penalty)

**Ví dụ:**
- Dạy robot đi bộ
- AI chơi game (AlphaGo)

---

## 3. Quy trình xây dựng mô hình ML

```
┌───────────────────────────────────────────────────────────────────┐
│                      QUY TRÌNH ML                                  │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ┌────────────┐    ┌────────────┐    ┌────────────────────┐      │
│   │ 1. Thu thập│───▶│ 2. Tiền xử │───▶│ 3. Trích xuất      │      │
│   │    dữ liệu │    │    lý      │    │    đặc trưng       │      │
│   └────────────┘    └────────────┘    │    (Features)      │      │
│                                       └──────────┬─────────┘      │
│                                                  │                 │
│   ┌────────────┐    ┌────────────┐    ┌──────────▼─────────┐      │
│   │ 6. Triển   │◀───│ 5. Đánh giá│◀───│ 4. Huấn luyện      │      │
│   │    khai    │    │    mô hình │    │    mô hình         │      │
│   └────────────┘    └────────────┘    └────────────────────┘      │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

### 3.1 Thu thập dữ liệu (Data Collection)

- Nguồn dữ liệu: Kaggle, công ty, tự thu thập
- **Dự án của ta**: 212,085 email đã gán nhãn

### 3.2 Tiền xử lý (Preprocessing)

```python
# Ví dụ tiền xử lý email trong dự án
- Loại bỏ HTML tags
- Chuẩn hóa khoảng trắng
- Chuyển về chữ thường
```

### 3.3 Trích xuất đặc trưng (Feature Engineering)

> **Đây là bước RẤT QUAN TRỌNG** - Xem chi tiết tại [FEATURE_EXTRACTION_GUIDE.md](./FEATURE_EXTRACTION_GUIDE.md)

**Đặc trưng (Feature)** là các thuộc tính số học mà mô hình có thể học được.

### 3.4 Chia dữ liệu (Train/Test Split)

```
Tổng dữ liệu: 212,085 emails
    │
    ├── 80% Training set: 169,668 emails
    │   (Để mô hình học)
    │
    └── 20% Testing set: 42,417 emails
        (Để đánh giá mô hình)
```

> 💡 **Tại sao cần chia?**  
> Nếu dùng toàn bộ dữ liệu để train, ta không biết mô hình hoạt động thế nào với dữ liệu mới. Testing set giả lập dữ liệu "chưa từng thấy".

### 3.5 Huấn luyện (Training)

```python
# Pseudo-code
model = XGBClassifier()
model.fit(X_train, y_train)  # X = features, y = labels
```

### 3.6 Đánh giá (Evaluation)

```python
predictions = model.predict(X_test)
accuracy = (predictions == y_test).mean()
# → 96% accuracy
```

---

## 4. Decision Tree (Cây quyết định)

### 4.1 Khái niệm

**Decision Tree** là thuật toán đưa ra quyết định bằng cách chia dữ liệu thành các nhánh dựa trên các điều kiện.

### 4.2 Ví dụ minh họa

```
                    [Email]
                       │
           ┌───────────┴───────────┐
           │                       │
    Có từ "urgent"?          Có từ "urgent"?
         YES                      NO
           │                       │
     ┌─────┴─────┐           ┌─────┴─────┐
     │           │           │           │
 Có link?    Có link?    Có link?    Có link?
   YES         NO          YES         NO
     │           │           │           │
 PHISHING   NGHI NGỜ    KIỂM TRA    AN TOÀN
```

### 4.3 Ưu và nhược điểm

| Ưu điểm | Nhược điểm |
|---------|------------|
| ✅ Dễ hiểu, dễ giải thích | ❌ Dễ overfitting với dữ liệu training |
| ✅ Không cần chuẩn hóa dữ liệu | ❌ Không ổn định (thay đổi nhỏ → kết quả khác) |
| ✅ Xử lý được cả số và danh mục | ❌ Không tối ưu với dữ liệu phức tạp |

### 4.4 Các khái niệm quan trọng

- **Node (Nút)**: Điểm đưa ra quyết định
- **Branch (Nhánh)**: Kết quả của một điều kiện
- **Leaf (Lá)**: Kết quả cuối cùng
- **Depth (Độ sâu)**: Số tầng của cây

---

## 5. Ensemble Methods (Phương pháp kết hợp)

### 5.1 Ý tưởng chính

> "Nhiều ý kiến tốt hơn một" - Kết hợp nhiều mô hình yếu → Một mô hình mạnh

```
Mô hình 1: 70% đúng  ─┐
Mô hình 2: 72% đúng  ─┼─→ Kết hợp → 90% đúng
Mô hình 3: 68% đúng  ─┘
```

### 5.2 Hai phương pháp chính

#### A. Bagging (Bootstrap Aggregating)

**Đại diện: Random Forest**

```
      Dữ liệu gốc
           │
    ┌──────┼──────┐
    ↓      ↓      ↓
 Sample1 Sample2 Sample3   ← Lấy mẫu ngẫu nhiên (có hoàn lại)
    │      │      │
    ↓      ↓      ↓
  Tree1  Tree2  Tree3      ← Train nhiều cây độc lập
    │      │      │
    └──────┼──────┘
           ↓
     Voting (Bỏ phiếu)     ← Kết quả = đa số
```

**Ví dụ:**
- Tree 1: Phishing
- Tree 2: Legitimate  
- Tree 3: Phishing
- **Kết quả: Phishing** (2/3)

#### B. Boosting

**Đại diện: XGBoost, AdaBoost, LightGBM**

```
  Tree 1: Dự đoán
      │
      ↓
  Sai sót của Tree 1
      │
      ↓
  Tree 2: Sửa sai sót Tree 1
      │
      ↓
  Sai sót còn lại
      │
      ↓
  Tree 3: Sửa sai sót Tree 2
      │
      ⋮
  Kết hợp tất cả Trees
```

> 💡 **Khác biệt chính:**  
> - Bagging: Các cây độc lập, train song song  
> - Boosting: Các cây phụ thuộc, train tuần tự

### 5.3 So sánh Bagging vs Boosting

| Tiêu chí | Bagging (Random Forest) | Boosting (XGBoost) |
|----------|-------------------------|-------------------|
| Cách hoạt động | Song song | Tuần Tự |
| Mục tiêu | Giảm variance (overfitting) | Giảm bias (underfitting) |
| Tốc độ train | Nhanh | Chậm hơn |
| Overfitting | Ít | Có thể nếu không tune |
| Độ chính xác | Tốt | Thường cao hơn ✅ |

---

## 6. XGBoost - Thuật toán trong dự án

### 6.1 XGBoost là gì?

**XGBoost** = e**X**treme **G**radient **Boost**ing

Là thuật toán Gradient Boosting được tối ưu hóa về:
- Tốc độ (sử dụng C++ backend)
- Hiệu suất (regularization tích hợp)
- Khả năng mở rộng (parallel processing)

### 6.2 Tại sao chọn XGBoost cho dự án?

| Lý do | Giải thích |
|-------|------------|
| 1. Hiệu suất cao với dữ liệu bảng | TF-IDF tạo ra ma trận thưa, XGBoost xử lý tốt |
| 2. Regularization | L1 + L2 giúp tránh overfitting |
| 3. Xử lý missing values | Tự động xử lý giá trị thiếu |
| 4. Feature importance | Giải thích được feature nào quan trọng |
| 5. Đã được chứng minh | Thắng nhiều cuộc thi Kaggle |

### 6.3 Các hyperparameter quan trọng

```python
XGBClassifier(
    n_estimators=200,      # Số cây quyết định
    max_depth=6,           # Độ sâu tối đa mỗi cây
    learning_rate=0.1,     # Tốc độ học (step size)
    subsample=0.8,         # % dữ liệu cho mỗi cây
    colsample_bytree=0.8,  # % feature cho mỗi cây
)
```

**Giải thích chi tiết:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `n_estimators` | 200 | Dùng 200 cây, mỗi cây sửa lỗi cây trước |
| `max_depth` | 6 | Cây không quá sâu → tránh overfitting |
| `learning_rate` | 0.1 | Học từ từ → kết quả ổn định hơn |
| `subsample` | 0.8 | Mỗi cây chỉ dùng 80% data → đa dạng hóa |
| `colsample_bytree` | 0.8 | Mỗi cây chỉ dùng 80% features → giảm overfitting |

### 6.4 Cách XGBoost hoạt động

```
Bước 1: Khởi tạo dự đoán ban đầu (thường là trung bình)
         Prediction_0 = 0.5 (50% phishing)
                │
                ▼
Bước 2: Tính residual (sai số)
         Residual_1 = Actual - Prediction_0
         (Email thực sự là phishing=1, dự đoán 0.5 → sai số = 0.5)
                │
                ▼
Bước 3: Train Tree_1 để dự đoán Residual_1
         Tree_1 học cách sửa sai số
                │
                ▼
Bước 4: Cập nhật prediction
         Prediction_1 = Prediction_0 + learning_rate × Tree_1
         0.7 = 0.5 + 0.1 × 2.0
                │
                ▼
Bước 5: Lặp lại với Tree_2, Tree_3, ... Tree_200
                │
                ▼
Kết quả: Prediction cuối = tổng hợp 200 trees
```

---

## 7. Các chỉ số đánh giá mô hình

### 7.1 Confusion Matrix (Ma trận nhầm lẫn)

```
                    Predicted
                    Hợp lệ    Lừa đảo
                  ┌─────────┬─────────┐
           Hợp lệ │   TN    │   FP    │  ← Predicted wrong (Type I Error)
Actual           ├─────────┼─────────┤
          Lừa đảo│   FN    │   TP    │  ← Predicted wrong (Type II Error)
                  └─────────┴─────────┘
```

**Giải thích:**
- **TP (True Positive)**: Dự đoán Phishing, thực tế là Phishing ✅
- **TN (True Negative)**: Dự đoán Hợp lệ, thực tế là Hợp lệ ✅
- **FP (False Positive)**: Dự đoán Phishing, thực tế là Hợp lệ ❌ 
- **FN (False Negative)**: Dự đoán Hợp lệ, thực tế là Phishing ❌

### 7.2 Accuracy (Độ chính xác)

```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
         = Số dự đoán đúng / Tổng số mẫu
         = 96% trong dự án của ta
```

### 7.3 Precision (Độ chính xác dương)

```
Precision = TP / (TP + FP)
          = Trong số email bị gắn nhãn "Phishing", bao nhiêu % thực sự là Phishing?
```

> 💡 **Khi nào quan trọng?**  
> Khi chi phí của False Positive cao. VD: Không muốn đánh email quan trọng vào spam.

### 7.4 Recall (Độ phủ / Sensitivity)

```
Recall = TP / (TP + FN)
       = Trong số email thực sự là Phishing, bao nhiêu % được phát hiện?
```

> 💡 **Khi nào quan trọng?**  
> Khi chi phí của False Negative cao. VD: Bỏ sót email lừa đảo nguy hiểm.

### 7.5 F1-Score

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

> **F1-Score** là trung bình điều hòa của Precision và Recall.  
> Dùng khi cần cân bằng cả hai.

### 7.6 Tổng hợp metrics của dự án

| Metric | Giá trị | Ý nghĩa |
|--------|---------|---------|
| Accuracy | 96% | 96% email được phân loại đúng |
| Precision (Phishing) | 96% | 96% email gắn "Phishing" thực sự là phishing |
| Recall (Phishing) | 96% | 96% email phishing được phát hiện |
| F1-Score | 0.9607 | Cân bằng tốt giữa precision và recall |

---

## 8. Tóm tắt và Lời khuyên

### 8.1 Kiến thức cần nhớ

✅ **Machine Learning** = Máy học từ dữ liệu  
✅ **Supervised Learning** = Học từ dữ liệu có nhãn  
✅ **Classification** = Phân loại vào các nhóm  
✅ **Decision Tree** = Chia nhánh theo điều kiện  
✅ **Ensemble** = Kết hợp nhiều mô hình  
✅ **XGBoost** = Boosting hiệu quả, từng cây sửa lỗi cây trước  
✅ **F1-Score** = Cân bằng Precision và Recall

### 8.2 Tài liệu tham khảo thêm

1. **Videos:**
   - StatQuest YouTube (Giải thích ML dễ hiểu)
   - 3Blue1Brown - Neural Networks

2. **Courses:**
   - Andrew Ng - Machine Learning (Coursera)
   - fast.ai - Practical Deep Learning

3. **Books:**
   - "Hands-On Machine Learning" - Aurélien Géron
   - "Introduction to Statistical Learning" - Free online

4. **Practice:**
   - Kaggle Competitions
   - scikit-learn documentation

---

## Câu hỏi ôn tập

1. Sự khác nhau giữa Supervised và Unsupervised Learning là gì?
2. Tại sao cần chia dữ liệu thành Training và Testing set?
3. Bagging và Boosting khác nhau như thế nào?
4. XGBoost thuộc loại Bagging hay Boosting?
5. Precision và Recall khác nhau như thế nào? Khi nào cần ưu tiên cái nào?
6. Tại sao F1-Score quan trọng?

---

*Tài liệu được tạo cho nhóm đồ án*  
*Cập nhật: Tháng 1/2026*
