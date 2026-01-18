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

#### 5.1 Giao diện Web FastAPI
- **Framework**: Sử dụng FastAPI để phát triển REST API và web application
- **Chức năng chính**:
  - RESTful API với OpenAPI/Swagger documentation tự động
  - Cho phép người dùng nhập nội dung email trực tiếp qua API
  - Tích hợp với Google Gmail API để thu thập email từ tài khoản Gmail của người dùng
  - Hiển thị kết quả dự đoán (phishing/non-phishing) với confidence score
  - Lưu trữ email và kết quả dự đoán vào SQLite database
  - Hiển thị lịch sử email và predictions đã phân tích
  - Frontend tách biệt (Vanilla JavaScript) giao tiếp với API qua REST endpoints

#### 5.2 Tích hợp Gmail API vào FastAPI
- **Cách hoạt động**: FastAPI application sử dụng Google Gmail API với OAuth2 authentication
- **Thiết lập Google Cloud Project**:
  - Tạo Google Cloud Project và enable Gmail API
  - Tạo OAuth2 credentials (Client ID và Client Secret)
  - Cấu hình authorized redirect URIs
- **Xác thực OAuth2**:
  - Người dùng kết nối tài khoản Gmail thông qua Google OAuth2 consent screen
  - Hệ thống nhận authorization code và exchange thành access token và refresh token
  - Hệ thống mã hóa và lưu trữ tokens vào SQLite database
  - Tự động refresh token khi hết hạn sử dụng refresh token
  - Xử lý lỗi authentication và yêu cầu re-authentication khi cần
- **Gmail API Client**:
  - Sử dụng `google-api-python-client` để tương tác với Gmail API
  - Implement wrapper để xử lý rate limits với exponential backoff
  - Xử lý các lỗi API (network, server, authentication)
- **Workflow**:
  1. Người dùng click "Connect Gmail" và được redirect đến Google OAuth2 consent screen
  2. Người dùng cấp quyền truy cập Gmail (read-only)
  3. Hệ thống nhận authorization code và exchange thành tokens
  4. Hệ thống mã hóa và lưu OAuth tokens vào database
  5. Người dùng click "Fetch Emails" để lấy email từ Gmail API
  6. Hệ thống sử dụng stored token để authenticate Gmail API requests
  7. Email được fetch và lưu vào SQLite database (tránh trùng lặp qua gmail_message_id)
  8. Email được tự động xử lý qua model đã đóng gói
  9. Kết quả prediction được lưu vào database kèm model version
  10. Kết quả được hiển thị trên GUI với confidence score

#### 5.3 Lưu trữ Dữ liệu với SQLite
- **Database**: Sử dụng SQLite để lưu trữ dữ liệu
- **Các bảng dữ liệu**:
  - **users**: 
    - `id` (INTEGER PRIMARY KEY)
    - `email` (TEXT UNIQUE) - Địa chỉ Gmail của người dùng
    - `created_at` (TIMESTAMP) - Thời gian tạo tài khoản
    - `last_login` (TIMESTAMP) - Lần đăng nhập cuối
  - **oauth_tokens**: 
    - `id` (INTEGER PRIMARY KEY)
    - `user_id` (INTEGER FOREIGN KEY -> users.id) - Liên kết với user
    - `encrypted_token` (BLOB) - OAuth access token đã mã hóa
    - `refresh_token` (BLOB) - Refresh token đã mã hóa
    - `expires_at` (TIMESTAMP) - Thời gian hết hạn token
    - `created_at` (TIMESTAMP) - Thời gian tạo
    - `updated_at` (TIMESTAMP) - Thời gian cập nhật
  - **emails**: 
    - `id` (INTEGER PRIMARY KEY)
    - `user_id` (INTEGER FOREIGN KEY -> users.id) - Liên kết với user
    - `gmail_message_id` (TEXT) - Message ID từ Gmail API (để tránh trùng lặp)
    - `subject` (TEXT) - Tiêu đề email
    - `sender` (TEXT) - Người gửi
    - `recipient` (TEXT) - Người nhận
    - `body` (TEXT) - Nội dung email đầy đủ
    - `received_at` (TIMESTAMP) - Thời gian nhận email (từ Gmail)
    - `fetched_at` (TIMESTAMP) - Thời gian fetch từ API
    - `created_at` (TIMESTAMP) - Thời gian lưu vào database
  - **predictions**: 
    - `id` (INTEGER PRIMARY KEY)
    - `email_id` (INTEGER FOREIGN KEY -> emails.id) - Liên kết với email
    - `prediction` (INTEGER) - 0 (benign) hoặc 1 (phishing)
    - `probability` (REAL) - Confidence score từ 0.0 đến 1.0
    - `model_version` (TEXT) - Phiên bản model sử dụng
    - `created_at` (TIMESTAMP) - Thời gian tạo prediction
- **Bảo mật**: 
  - OAuth tokens được mã hóa bằng Fernet symmetric encryption trước khi lưu
  - Encryption key được lưu trong environment variable
  - Tokens không bao giờ được log hoặc hiển thị dưới dạng plain text
- **Chức năng**:
  - Lưu trữ email và predictions để phân tích lịch sử
  - Hỗ trợ nhiều người dùng với dữ liệu riêng biệt (isolation qua user_id)
  - Truy vấn và hiển thị lịch sử email đã phân tích
  - Hỗ trợ multiple predictions cho cùng một email (để tracking model versions)
  - Tránh trùng lặp email qua gmail_message_id

#### 5.4 Sử dụng Model đã đóng gói
- **Load model**: Flask load model package khi khởi động (lazy loading để tối ưu)
- **Cache model**: Model được cache trong memory để tăng tốc độ dự đoán
- **Xử lý dữ liệu**: Email mới được xử lý qua các preprocessor đã lưu trong model package
- **Lưu trữ predictions**: Kết quả dự đoán được lưu vào database kèm model version để tracking

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
- Thiết lập Google Cloud Project và enable Gmail API
- Phân tích cấu trúc dataset ban đầu

#### Tuần 3-4: Tiền xử lý và NLP Cơ bản
- Làm sạch dữ liệu với Pandas
- Chuẩn hóa nhãn và nội dung email
- Implement các kỹ thuật NLP cơ bản:
  - Tokenization
  - Loại bỏ stopwords
  - Stemming/Lemmatization
- Thiết kế và tạo SQLite database schema
- Implement OAuth2 authentication flow cho Gmail API

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

#### Tuần 11-12: FastAPI REST API, Frontend và Phân tích Triển khai
- Phát triển FastAPI REST API với OpenAPI documentation
- Tích hợp Gmail API vào FastAPI để thu thập email
- Implement OAuth2 authentication và token management
- Tích hợp SQLite database với FastAPI application
- Tích hợp model đã đóng gói vào FastAPI để dự đoán
- Phát triển frontend (Vanilla JavaScript) giao tiếp với REST API:
  - Kết nối tài khoản Gmail qua OAuth2
  - Fetch email từ Gmail API
  - Nhập email trực tiếp
  - Hiển thị kết quả dự đoán với confidence score
  - Xem lịch sử email và predictions đã phân tích
- Implement token encryption và secure storage
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
- **Google Gmail API**: API chính thức để truy cập email từ Gmail
  - **google-api-python-client**: Client library cho Gmail API
  - **google-auth-oauthlib**: OAuth2 authentication flow
- **SQLite**: Database để lưu trữ dữ liệu (users, emails, tokens, predictions)
- **cryptography**: Mã hóa OAuth tokens trước khi lưu vào database
- **Matplotlib/Seaborn**: Visualization
- **FastAPI**: Phát triển REST API và web application
- **Uvicorn**: ASGI server để chạy FastAPI application
- **Pydantic**: Data validation và serialization
- **Vanilla JavaScript**: Frontend framework (không sử dụng framework bên ngoài)
- **pickle/joblib**: Đóng gói và lưu trữ mô hình ML

## Kết quả Mong đợi

1. Mô hình ML có độ chính xác cao trong việc phát hiện email phishing
2. Hệ thống tích hợp Gmail API hoạt động ổn định và bảo mật để thu thập email
3. SQLite database lưu trữ đầy đủ email, predictions, và user tokens (đã mã hóa)
4. OAuth2 authentication flow hoạt động mượt mà với token refresh tự động
5. Prototype/demo hoạt động tốt và dễ sử dụng với REST API (FastAPI) và frontend (Vanilla JavaScript)
6. Hệ thống hỗ trợ nhiều người dùng với dữ liệu riêng biệt
7. Tài liệu phân tích triển khai thực tế và đề xuất tích hợp với các cơ chế bảo mật truyền thống

