# Phishing Detection API

API phát hiện email phishing sử dụng Machine Learning.

## Cài đặt

### Sử dụng uv (khuyến nghị)

```bash
# Cài đặt uv nếu chưa có
curl -LsSf https://astral.sh/uv/install.sh | sh

# Tạo virtual environment và cài đặt dependencies
uv venv
source .venv/bin/activate  # Linux/Mac
# hoặc .venv\Scripts\activate  # Windows

uv pip install -e .
```

### Sử dụng pip truyền thống

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

## Cấu hình

1. Copy file `.env.example` thành `.env`:
```bash
cp app/.env.example app/.env
```

2. Cập nhật các biến môi trường trong `app/.env`:
```env
# Gmail OAuth2 credentials
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback

# Security
SECRET_KEY=your_secret_key_here

# Database
DATABASE_PATH=data/phishing_detection.db

# ML Model
MODEL_PATH=models/xgboost.joblib
```

## Khởi tạo Database

```bash
python scripts/init_database.py
```

## Chạy Server

### Development
```bash
python run.py
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Sau khi chạy server, truy cập:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

## Testing

### Test API endpoints
```bash
python scripts/test_api.py
```

### Test với curl

#### 1. Kiểm tra trạng thái xác thực
```bash
curl http://localhost:8000/api/v1/auth/status
```

#### 2. Phân tích email (không cần đăng nhập)
```bash
curl -X POST http://localhost:8000/api/v1/predictions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "email_text": "Dear customer, please verify your account by clicking this link: http://suspicious-site.com/verify",
    "subject": "Urgent: Account Verification Required"
  }'
```

#### 3. Bắt đầu OAuth2 flow
```bash
curl -X POST http://localhost:8000/api/v1/auth/connect
```

## API Endpoints

### Authentication
- `GET /api/v1/auth/status` - Kiểm tra trạng thái xác thực
- `POST /api/v1/auth/connect` - Bắt đầu OAuth2 flow
- `GET /api/v1/auth/callback` - OAuth2 callback
- `POST /api/v1/auth/disconnect` - Ngắt kết nối Gmail

### Emails
- `POST /api/v1/emails/fetch` - Fetch emails từ Gmail (cần auth)
- `GET /api/v1/emails/list` - Danh sách emails (cần auth)
- `GET /api/v1/emails/{email_id}` - Chi tiết email (cần auth)
- `GET /api/v1/emails/{email_id}/predictions` - Lịch sử predictions của email (cần auth)

### Predictions
- `POST /api/v1/predictions/analyze` - Phân tích email text (không cần auth)
- `POST /api/v1/predictions/analyze-email/{email_id}` - Phân tích email đã lưu (cần auth)

### History
- `GET /api/v1/history/predictions` - Lịch sử predictions (cần auth)

## Response Models

Chi tiết về các response models xem tại [docs/RESPONSE_MODELS.md](docs/RESPONSE_MODELS.md)

### Common Response Format

#### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Optional message"
}
```

#### Error Response
```json
{
  "success": false,
  "error": "Error details",
  "message": "User-friendly message"
}
```

### Prediction Response
```json
{
  "success": true,
  "data": {
    "prediction": 1,
    "classification": "SUSPICIOUS",
    "probability": 0.85,
    "ensemble_score": 0.42,
    "threshold": 0.3,
    "suspicious_margin": 0.2,
    "is_phishing": false,
    "is_suspicious": true,
    "features": {
      "links_count": 2,
      "has_attachment": 0,
      "urgent_keywords": 1,
      "sender_domain": "suspicious-site.com"
    }
  }
}
```

### Classification Levels
- `LEGITIMATE`: Email an toàn
- `SUSPICIOUS`: Email đáng ngờ, cần cảnh giác
- `PHISHING`: Email phishing, nguy hiểm

## Project Structure

```
.
├── app/
│   ├── api/v1/endpoints/    # API endpoints
│   ├── core/                # Core config & security
│   ├── db/                  # Database session
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   ├── utils/               # Utilities
│   └── main.py              # FastAPI app
├── docs/                    # Documentation
├── models/                  # ML models
├── scripts/                 # Utility scripts
├── src/                     # ML source code
├── pyproject.toml           # Project config (uv)
├── requirements.txt         # Dependencies (pip)
└── run.py                   # Entry point
```

## Development

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings to functions

### Logging
Logs được lưu tại `logs/app.log` với format:
```
[2024-01-15 10:30:00] [INFO] [module] Message [context]
```

### Database
- SQLite database tại `data/phishing_detection.db`
- Schema được quản lý trong `app/db/session.py`
- Migrations: Chạy `python scripts/init_database.py`

## Troubleshooting

### Database locked error
```bash
# Đóng tất cả connections và restart
rm data/phishing_detection.db
python scripts/init_database.py
```

### Model not found
```bash
# Đảm bảo model file tồn tại
ls -la models/xgboost.joblib
```

### OAuth2 errors
- Kiểm tra `GMAIL_CLIENT_ID` và `GMAIL_CLIENT_SECRET`
- Đảm bảo `GMAIL_REDIRECT_URI` khớp với Google Console
- Kiểm tra scopes trong Google Console

## License

MIT
