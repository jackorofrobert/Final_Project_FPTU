# Quick Start Guide

Hướng dẫn nhanh để chạy Phishing Detection API.

## 1. Cài đặt Dependencies

### Sử dụng uv (khuyến nghị - nhanh hơn)
```bash
# Cài đặt uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Cài đặt dependencies
make install-uv
# hoặc
uv venv && uv pip install -e .
```

### Sử dụng pip
```bash
make install
# hoặc
pip install -r requirements.txt
```

## 2. Cấu hình

```bash
# Copy file .env mẫu
cp app/.env.example app/.env

# Chỉnh sửa app/.env với thông tin của bạn
# Ít nhất cần cập nhật:
# - SECRET_KEY (generate random string)
# - GMAIL_CLIENT_ID (nếu dùng Gmail OAuth)
# - GMAIL_CLIENT_SECRET (nếu dùng Gmail OAuth)
```

## 3. Khởi tạo Database

```bash
make init-db
# hoặc
python scripts/init_database.py
```

## 4. Chạy Server

```bash
make run
# hoặc
python run.py
```

Server sẽ chạy tại: http://localhost:8000

## 5. Test API

### Mở trình duyệt
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Test với script
```bash
make test-api
# hoặc
python scripts/test_api.py
```

### Test với curl
```bash
# Phân tích email phishing
curl -X POST http://localhost:8000/api/v1/predictions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "URGENT! Your account will be suspended. Click here immediately: http://fake-bank.com/verify",
    "subject": "Account Suspension Warning"
  }'
```

## 6. Các lệnh hữu ích

```bash
# Xem tất cả lệnh có sẵn
make help

# Generate OpenAPI schema
make generate-openapi

# Clean temporary files
make clean

# Run với auto-reload (development)
make dev
```

## Ví dụ sử dụng API

### 1. Phân tích email đơn giản
```python
import requests

response = requests.post('http://localhost:8000/api/v1/predictions/analyze', json={
    'email_text': 'Dear customer, verify your account now!',
    'subject': 'Urgent: Account Verification'
})

result = response.json()
print(f"Classification: {result['data']['classification']}")
print(f"Is Phishing: {result['data']['is_phishing']}")
print(f"Probability: {result['data']['probability']}")
```

### 2. Phân tích với features bổ sung
```python
response = requests.post('http://localhost:8000/api/v1/predictions/analyze', json={
    'email_text': 'Click here to claim your prize!',
    'subject': 'You won $1,000,000!',
    'has_attachment': 1,
    'links_count': 3,
    'sender_domain': 'suspicious-site.com',
    'urgent_keywords': 1
})

result = response.json()
print(f"Classification: {result['data']['classification']}")
print(f"Ensemble Score: {result['data']['ensemble_score']}")
```

### 3. Kiểm tra trạng thái xác thực
```python
response = requests.get('http://localhost:8000/api/v1/auth/status')
result = response.json()
print(f"Authenticated: {result['data']['authenticated']}")
```

## Troubleshooting

### Lỗi: Module not found
```bash
# Đảm bảo đã cài đặt dependencies
make install
# hoặc
make install-uv
```

### Lỗi: Database locked
```bash
# Xóa database cũ và tạo lại
rm -rf data/
make init-db
```

### Lỗi: Model not found
```bash
# Kiểm tra model file tồn tại
ls -la models/xgboost.joblib

# Nếu không có, train model trước
python src/train.py
```

### Lỗi: Port already in use
```bash
# Thay đổi port trong run.py hoặc chạy với port khác
uvicorn app.main:app --port 8001
```

## Tiếp theo

- Đọc [README_API.md](README_API.md) để biết chi tiết về API
- Xem [docs/RESPONSE_MODELS.md](docs/RESPONSE_MODELS.md) để hiểu response format
- Xem [docs/api.md](docs/api.md) để biết thêm về endpoints

## Cần trợ giúp?

- Kiểm tra logs tại `logs/app.log`
- Xem API documentation tại http://localhost:8000/docs
- Đọc source code trong `app/` directory
