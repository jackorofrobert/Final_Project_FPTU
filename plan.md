# Kế hoạch Dự án: Hệ thống Phát hiện Email Phishing

## Tổng quan

Dự án xây dựng một hệ thống phát hiện email phishing dựa trên Machine Learning, sử dụng các kỹ thuật NLP và các mô hình ML để phân loại email là phishing hay không.

## Phân tích Chi tiết Requirement

### 1. Thu thập và Tiền xử lý Dữ liệu

#### 1.1 Thu thập dữ liệu
- **Nguồn dữ liệu chính**: Email Phishing Dataset từ Kaggle
- **Công cụ**: Pandas để xử lý và quản lý dữ liệu
- **Mục tiêu**: Thu thập dataset đủ lớn và đa dạng để huấn luyện mô hình

#### 1.2 Tiền xử lý dữ liệu
- **Làm sạch dữ liệu**:
  - Loại bỏ email trùng lặp
  - Xử lý missing values
  - Chuẩn hóa định dạng email
- **Chuẩn hóa nhãn**:
  - Đảm bảo nhãn nhất quán (phishing/non-phishing)
  - Cân bằng dataset nếu cần
- **Chuẩn hóa nội dung email**:
  - Loại bỏ HTML tags
  - Xử lý encoding issues
  - Chuẩn hóa whitespace

### 2. Xử lý NLP và Trích xuất Đặc trưng

#### 2.1 Xử lý NLP
- **Tokenization**: Chia email thành các tokens
- **Loại bỏ stopwords**: Xóa các từ phổ biến không có ý nghĩa
- **Stemming/Lemmatization**: Chuẩn hóa các từ về dạng gốc
- **Mục tiêu**: Tạo ra các features từ nội dung email

#### 2.2 Trích xuất đặc trưng
- **TF-IDF (Term Frequency-Inverse Document Frequency)**:
  - Đo lường tầm quan trọng của từ trong email
  - Tạo vector đặc trưng từ nội dung
- **CountVectorizer**:
  - Đếm tần suất xuất hiện của từ
  - Tạo bag-of-words representation
- **Đặc trưng từ URL**:
  - Phát hiện và trích xuất URL trong email
  - Phân tích domain, path, parameters
  - Kiểm tra URL shortening, suspicious domains
- **Đặc trưng từ Header email**:
  - Phân tích From, To, Subject, Date
  - Kiểm tra SPF, DKIM, DMARC records
  - Phát hiện email spoofing

### 3. Huấn luyện và So sánh Mô hình ML

#### 3.1 Mô hình được sử dụng
- **HistGradientBoosting (HGB)**:
  - Gradient Boosting hiện đại từ scikit-learn
  - Xử lý tốt dữ liệu lớn
  - Hiệu suất cao với dữ liệu có nhiều features
- **XGBoost (XGB)**:
  - Extreme Gradient Boosting
  - Tối ưu hóa hiệu suất và tốc độ
  - Xử lý tốt overfitting

#### 3.2 Tối ưu Siêu tham số
- **GridSearchCV**: Tìm kiếm toàn diện trên grid của tham số
- **RandomizedSearchCV**: Tìm kiếm ngẫu nhiên hiệu quả hơn với không gian tham số lớn
- **Tham số cần tối ưu**:
  - Learning rate
  - Max depth
  - Number of estimators
  - Regularization parameters

#### 3.3 Đóng gói Mô hình
- **Mục đích**: Đóng gói mô hình đã huấn luyện để có thể tái sử dụng và triển khai dễ dàng
- **Công cụ**: Sử dụng pickle hoặc joblib để serialize mô hình
- **Nội dung package**:
  - Mô hình đã huấn luyện (HGB hoặc XGBoost)
  - Các preprocessor cần thiết (TF-IDF vectorizer, CountVectorizer)
  - Metadata: version, training date, performance metrics (Accuracy, Precision, Recall, F1-score, ROC-AUC)
- **Lưu trữ**: Model package được lưu trong thư mục `models/` để dễ quản lý và version control

### 4. Đánh giá Mô hình

#### 4.1 Metrics đánh giá
- **Accuracy**: Tỷ lệ dự đoán đúng tổng thể
- **Precision**: Tỷ lệ email được dự đoán là phishing thực sự là phishing
- **Recall**: Tỷ lệ email phishing thực tế được phát hiện
- **F1-score**: Harmonic mean của Precision và Recall
- **ROC-AUC**: Diện tích dưới đường cong ROC, đo khả năng phân biệt của mô hình

#### 4.2 Visualization
- **Confusion Matrix**: Ma trận nhầm lẫn để xem chi tiết các loại lỗi
- **ROC Curve**: Đường cong ROC để đánh giá hiệu suất phân loại
- **Feature Importance**: Biểu đồ tầm quan trọng của các features

### 5. Prototype/Demo

#### 5.1 Giao diện Web Flask
- **Framework**: Sử dụng Flask để phát triển web application
- **Chức năng chính**:
  - Cho phép người dùng nhập nội dung email trực tiếp
  - Tích hợp với tool Playwright để thu thập email từ các nguồn (Gmail, Outlook, etc.)
  - Hiển thị kết quả dự đoán (phishing/non-phishing) với confidence score
  - Hiển thị các features quan trọng ảnh hưởng đến quyết định
  - Tự động xử lý email từ Playwright và hiển thị kết quả

#### 5.2 Tích hợp Playwright vào Flask
- **Cách hoạt động**: Flask application gọi tool Playwright thông qua API endpoints
- **Xử lý bất đồng bộ**: Sử dụng background tasks (threading hoặc Celery) để tránh block request khi Playwright đang chạy
- **Workflow**:
  1. Người dùng chọn nguồn email (Gmail, Outlook, etc.)
  2. Flask gọi Playwright để lấy email
  3. Email được tự động xử lý qua model đã đóng gói
  4. Kết quả được hiển thị trên GUI

#### 5.3 Sử dụng Model đã đóng gói
- **Load model**: Flask load model package khi khởi động (lazy loading để tối ưu)
- **Cache model**: Model được cache trong memory để tăng tốc độ dự đoán
- **Xử lý dữ liệu**: Email mới được xử lý qua các preprocessor đã lưu trong model package

### 6. Phân tích Triển khai Thực tế

#### 6.1 Tích hợp với Cơ chế Bảo mật Truyền thống
- **SPAM Filter**: Kết hợp với spam filter hiện có để tăng độ chính xác
- **DMARC (Domain-based Message Authentication, Reporting & Conformance)**: Xác thực domain gửi email
- **SPF (Sender Policy Framework)**: Kiểm tra quyền gửi email từ domain
- **DKIM (DomainKeys Identified Mail)**: Xác thực chữ ký email

#### 6.2 Đề xuất Triển khai
- Phân tích cách kết hợp mô hình ML với các cơ chế bảo mật truyền thống
- Đề xuất kiến trúc hệ thống tích hợp
- Phân tích hiệu quả và chi phí triển khai

## Timeline 3 Tháng

### Tháng 1: Thu thập Dữ liệu và Tiền xử lý

#### Tuần 1-2: Thu thập và Setup
- Tải Email Phishing Dataset từ Kaggle
- Thiết lập môi trường phát triển (Python, libraries)
- Bắt đầu phát triển tool Playwright để thu thập email bổ sung
- Phân tích cấu trúc dataset ban đầu

#### Tuần 3-4: Tiền xử lý và NLP Cơ bản
- Làm sạch dữ liệu với Pandas
- Chuẩn hóa nhãn và nội dung email
- Implement các kỹ thuật NLP cơ bản:
  - Tokenization
  - Loại bỏ stopwords
  - Stemming/Lemmatization
- Hoàn thiện tool Playwright để lấy email từ các nguồn

### Tháng 2: Trích xuất Đặc trưng và Huấn luyện Mô hình

#### Tuần 5-6: Trích xuất Đặc trưng
- Implement TF-IDF vectorization
- Implement CountVectorizer
- Trích xuất đặc trưng từ URL trong email
- Trích xuất đặc trưng từ header email
- Kết hợp tất cả các features

#### Tuần 7-8: Huấn luyện, Tối ưu và Đóng gói Model
- Huấn luyện mô hình HistGradientBoosting
- Huấn luyện mô hình XGBoost
- Tối ưu siêu tham số bằng GridSearchCV/RandomizedSearchCV
- So sánh hiệu suất giữa hai mô hình
- Chọn mô hình tốt nhất
- Đóng gói mô hình đã chọn cùng với preprocessors (sử dụng pickle/joblib)
- Lưu trữ model package kèm metadata (version, training date, metrics)

### Tháng 3: Đánh giá, Prototype và Triển khai

#### Tuần 9-10: Đánh giá và Visualization
- Đánh giá mô hình với các metrics: Accuracy, Precision, Recall, F1-score, ROC-AUC
- Tạo confusion matrix
- Vẽ ROC curve
- Phân tích feature importance
- Tạo báo cáo đánh giá chi tiết

#### Tuần 11-12: Flask GUI, Prototype/Demo và Phân tích Triển khai
- Phát triển Flask web application với GUI
- Tích hợp tool Playwright vào Flask để thu thập email
- Tích hợp model đã đóng gói vào Flask để dự đoán
- Phát triển giao diện web cho phép:
  - Nhập email trực tiếp
  - Sử dụng Playwright để lấy email từ các nguồn
  - Hiển thị kết quả dự đoán với confidence score
- Phân tích khả năng triển khai thực tế
- Nghiên cứu tích hợp với SPAM filter, DMARC, SPF, DKIM
- Viết tài liệu và đề xuất kiến trúc triển khai
- Hoàn thiện dự án và chuẩn bị báo cáo cuối cùng

## Công cụ và Thư viện

- **Python**: Ngôn ngữ lập trình chính
- **Pandas**: Xử lý và quản lý dữ liệu
- **scikit-learn**: NLP, feature extraction, ML models (HistGradientBoosting)
- **XGBoost**: Mô hình XGBoost
- **NLTK/spaCy**: Xử lý ngôn ngữ tự nhiên
- **Playwright**: Tool tự động hóa để thu thập email
- **Matplotlib/Seaborn**: Visualization
- **Flask**: Phát triển web application và GUI
- **pickle/joblib**: Đóng gói và lưu trữ mô hình ML

## Kết quả Mong đợi

1. Mô hình ML có độ chính xác cao trong việc phát hiện email phishing
2. Tool Playwright hoạt động ổn định để thu thập email từ các nguồn
3. Prototype/demo hoạt động tốt và dễ sử dụng
4. Tài liệu phân tích triển khai thực tế và đề xuất tích hợp với các cơ chế bảo mật truyền thống

