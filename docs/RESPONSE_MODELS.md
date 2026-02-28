# API Response Models Documentation

Tài liệu này mô tả các response models (schemas) được sử dụng trong API.

## Common Responses

### SuccessResponse
Response thành công chung cho tất cả endpoints.

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully"
}
```

**Fields:**
- `success` (boolean): Luôn là `true` khi request thành công
- `data` (any, optional): Dữ liệu trả về
- `message` (string, optional): Thông báo thành công

### ErrorResponse
Response lỗi chung cho tất cả endpoints.

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Invalid input provided"
}
```

**Fields:**
- `success` (boolean): Luôn là `false` khi có lỗi
- `error` (string, optional): Mã lỗi hoặc chi tiết lỗi
- `message` (string, optional): Thông báo lỗi dễ hiểu

---

## Authentication Responses

### AuthStatus
Trạng thái xác thực của user.

```json
{
  "authenticated": true,
  "user_id": 1,
  "user_email": "user@example.com"
}
```

**Fields:**
- `authenticated` (boolean): User đã xác thực hay chưa
- `user_id` (integer, optional): ID của user nếu đã xác thực
- `user_email` (string, optional): Email của user nếu đã xác thực

### OAuthConnect
URL để bắt đầu OAuth2 flow.

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
  "state": "random_state_string_12345"
}
```

**Fields:**
- `authorization_url` (string): URL để redirect user đến trang xác thực OAuth2
- `state` (string): State parameter để bảo vệ CSRF

---

## Email Responses

### EmailFetchResponse
Kết quả fetch emails từ Gmail.

```json
{
  "count": 3,
  "emails": [
    {
      "id": 1,
      "gmail_message_id": "abc123",
      "subject": "Test Email",
      "sender": "sender@example.com",
      "recipient": "recipient@example.com"
    }
  ]
}
```

**Fields:**
- `count` (integer): Số lượng emails đã fetch và lưu
- `emails` (array): Danh sách các email objects

### EmailListResponse
Danh sách emails với pagination.

```json
{
  "emails": [
    {
      "id": 1,
      "subject": "Test Email",
      "sender": "sender@example.com",
      "prediction": null
    }
  ],
  "limit": 50,
  "offset": 0
}
```

**Fields:**
- `emails` (array): Danh sách email objects
- `limit` (integer): Số lượng emails tối đa trả về
- `offset` (integer): Số lượng emails đã bỏ qua

### EmailDetail
Chi tiết đầy đủ của một email.

```json
{
  "id": 1,
  "user_id": 1,
  "gmail_message_id": "abc123",
  "subject": "Important: Verify Your Account",
  "sender": "noreply@example.com",
  "recipient": "user@example.com",
  "body": "Please verify your account...",
  "received_at": "2024-01-15T10:30:00Z",
  "fetched_at": "2024-01-15T10:35:00Z",
  "created_at": "2024-01-15T10:35:00Z",
  "prediction": {
    "id": 1,
    "prediction": 1,
    "probability": 0.95,
    "is_phishing": true
  }
}
```

**Fields:**
- `id` (integer): ID của email record
- `user_id` (integer): ID của user sở hữu email
- `gmail_message_id` (string): Gmail message ID
- `subject` (string, optional): Tiêu đề email
- `sender` (string, optional): Địa chỉ người gửi
- `recipient` (string, optional): Địa chỉ người nhận
- `body` (string, optional): Nội dung email
- `received_at` (string, optional): Thời gian nhận email (ISO format)
- `fetched_at` (string, optional): Thời gian fetch email (ISO format)
- `created_at` (string, optional): Thời gian tạo record (ISO format)
- `prediction` (object, optional): Kết quả dự đoán mới nhất

---

## Prediction Responses

### PredictionResponse
Kết quả phân tích phishing.

```json
{
  "prediction": 1,
  "classification": "SUSPICIOUS",
  "probability": 0.85,
  "ensemble_score": 0.42,
  "threshold": 0.3,
  "suspicious_margin": 0.2,
  "email_id": 123,
  "is_phishing": false,
  "is_suspicious": true,
  "features": {
    "links_count": 2,
    "has_attachment": 0,
    "urgent_keywords": 1,
    "sender_domain": "suspicious-site.com"
  }
}
```

**Fields:**
- `prediction` (integer): Kết quả dự đoán (0 = benign, 1 = phishing/suspicious)
- `classification` (string): Mức độ phân loại: `LEGITIMATE`, `SUSPICIOUS`, hoặc `PHISHING`
- `probability` (float): Độ tin cậy của model (0.0 - 1.0)
- `ensemble_score` (float, optional): Điểm tổng hợp từ model + feature risks (0.0 - 1.0)
- `threshold` (float): Ngưỡng phân loại
- `suspicious_margin` (float, optional): Margin trên threshold cho suspicious
- `email_id` (integer, optional): ID của email record nếu đã lưu
- `is_phishing` (boolean): Email có phải phishing không (PHISHING level)
- `is_suspicious` (boolean, optional): Email có phải suspicious không (SUSPICIOUS level)
- `features` (object, optional): Các features dùng để dự đoán
- `formula_details` (object, optional): Chi tiết công thức tính điểm

**Classification Levels:**
- `LEGITIMATE`: Email an toàn
- `SUSPICIOUS`: Email đáng ngờ, cần cảnh giác
- `PHISHING`: Email phishing, nguy hiểm

### PredictionDetailResponse
Chi tiết đầy đủ của một prediction.

```json
{
  "prediction": {
    "id": 1,
    "email_id": 123,
    "prediction": 1,
    "probability": 0.95,
    "model_version": "1.0.0",
    "created_at": "2024-01-15T10:40:00Z"
  },
  "result": {
    "prediction": 1,
    "probability": 0.95,
    "threshold": 0.5
  },
  "is_phishing": true
}
```

**Fields:**
- `prediction` (object): Prediction record với metadata
  - `id` (integer): ID của prediction
  - `email_id` (integer): ID của email
  - `prediction` (integer): Kết quả (0 hoặc 1)
  - `probability` (float): Độ tin cậy
  - `model_version` (string): Phiên bản model
  - `created_at` (string): Thời gian tạo
- `result` (object): Chi tiết kết quả
- `is_phishing` (boolean): Email có phải phishing không

---

## History Responses

### HistoryListResponse
Danh sách lịch sử predictions với pagination.

```json
{
  "predictions": [
    {
      "id": 1,
      "email_id": 123,
      "prediction": 1,
      "probability": 0.95,
      "model_version": "1.0.0",
      "created_at": "2024-01-15T10:40:00Z",
      "email": {
        "id": 123,
        "subject": "Verify Your Account",
        "sender": "noreply@example.com"
      }
    }
  ],
  "limit": 100,
  "offset": 0
}
```

**Fields:**
- `predictions` (array): Danh sách prediction history records
- `limit` (integer): Số lượng predictions tối đa trả về
- `offset` (integer): Số lượng predictions đã bỏ qua

### HistoryDetail
Chi tiết của một prediction history record.

```json
{
  "id": 1,
  "email_id": 123,
  "prediction": 1,
  "probability": 0.95,
  "model_version": "1.0.0",
  "created_at": "2024-01-15T10:40:00Z",
  "email": {
    "id": 123,
    "subject": "Verify Your Account",
    "sender": "noreply@example.com"
  }
}
```

**Fields:**
- `id` (integer): ID của prediction record
- `email_id` (integer): ID của email đã phân tích
- `prediction` (integer): Kết quả (0 = benign, 1 = phishing)
- `probability` (float): Độ tin cậy (0.0 - 1.0)
- `model_version` (string, optional): Phiên bản model đã dùng
- `created_at` (string): Thời gian tạo prediction (ISO format)
- `email` (object, optional): Chi tiết email liên quan

---

## Request Models

### PredictionRequest
Request để phân tích email.

```json
{
  "email_text": "Dear customer, please verify your account...",
  "subject": "Urgent: Account Verification Required",
  "has_attachment": 0,
  "links_count": 1,
  "sender_domain": "suspicious-site.com",
  "urgent_keywords": 1
}
```

**Fields:**
- `email_text` (string, required): Nội dung email cần phân tích
- `subject` (string, optional): Tiêu đề email
- `has_attachment` (integer, optional): Email có attachment không (0 hoặc 1)
- `links_count` (integer, optional): Số lượng links (tự động extract nếu không cung cấp)
- `sender_domain` (string, optional): Domain của người gửi (tự động extract nếu không cung cấp)
- `urgent_keywords` (integer, optional): Email có từ khóa khẩn cấp không (0 hoặc 1, tự động detect nếu không cung cấp)

### EmailFetchRequest
Request để fetch emails từ Gmail.

```json
{
  "max_results": 50
}
```

**Fields:**
- `max_results` (integer): Số lượng emails tối đa cần fetch (1-500, mặc định 50)

### OAuthCallback
Request callback từ OAuth2 provider.

```json
{
  "code": "authorization_code_from_provider",
  "state": "state_parameter_for_verification"
}
```

**Fields:**
- `code` (string): Authorization code từ OAuth2 provider
- `state` (string): State parameter để verify CSRF protection
