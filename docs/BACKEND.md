# Tài liệu Backend — PhishGuard

Tài liệu mô tả kiến trúc, luồng xử lý và giao diện lập trình ứng dụng (API) của backend hệ thống phát hiện email lừa đảo. Backend sử dụng FastAPI, SQLite và tích hợp ba dịch vụ bên ngoài: Mail API, VirusTotal và Google Gemini.

---

## 1. Tổng quan

| Thuộc tính | Giá trị |
|------------|--------|
| Framework | FastAPI (async) |
| Cơ sở dữ liệu | SQLite (`data/app.db`) |
| ORM | SQLAlchemy (async) |
| Xác thực | Session-based (cookie ký bằng `SECRET_KEY`) |
| Scheduler | APScheduler (AsyncIOScheduler) |
| ML runtime | Pipeline XGBoost (`joblib`) |
| Dịch vụ bên ngoài | Mail API (tự host), VirusTotal v3, Google Gemini |

### 1.1 Mô hình phân lớp

```
app/
├── api/v1/endpoints/     ← Lớp router: nhận HTTP request, validate schema
├── schemas/              ← Pydantic schema (input/output)
├── services/             ← Lớp nghiệp vụ, gọi model DB + tích hợp ngoài
├── models/               ← SQLAlchemy ORM model
├── db/                   ← Session, engine
├── core/                 ← Config, security, dependencies
├── utils/                ← Logger, helper, response wrapper
└── main.py               ← Entry point, CORS, middleware, startup/shutdown
```

Mọi request đi theo thứ tự `endpoint → service → model → DB`. Endpoint không được phép truy cập DB trực tiếp.

---

## 2. Cấu hình

### 2.1 File cấu hình

- [app/core/config.py](../app/core/config.py) — `Settings` kế thừa `BaseSettings`, tự động load từ `app/.env`.
- [app/config.py](../app/config.py) — Lớp `Config` legacy dùng cho kịch bản test/dev cũ.
- [app/.env.example](../app/.env.example) — Template biến môi trường.

### 2.2 Biến môi trường quan trọng

```env
# Database + storage
DATABASE_PATH=data/app.db
ATTACHMENT_DIR=data/attachments              # blob root cho attachment đã fetch
ATTACHMENT_MAX_SIZE_BYTES=33554432           # 32 MB — trùng cap upload free của VT

# Session & CORS
SECRET_KEY=<random-string>
SESSION_COOKIE_SECURE=false           # true khi chạy HTTPS
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
CORS_ORIGINS=["http://localhost:5001","http://localhost:3000"]

# Mail API (tự host)
MAIL_API_BASE_URL=http://localhost:8095
MAIL_API_TOKEN=<app-secret>

# Machine learning
MODEL_PATH=models/model.joblib

# VirusTotal
VIRUSTOTAL_API_KEY=<api-key>
VIRUSTOTAL_DAILY_LIMIT=200

# Gemini (Google AI Studio)
GOOGLE_AI_API_KEY=<api-key>
GOOGLE_AI_API_KEYS=["k1","k2"]        # failover giữa nhiều key
GEMINI_TRANSLATION_MODEL=gemini-3-flash-preview
TRANSLATION_CHUNK_MAX_CHARS=4000
TRANSLATION_MAX_INPUT_CHARS=120000
```

---

## 3. Xác thực

Hệ thống dùng cơ chế **session-based authentication** thay cho OAuth. Người dùng đăng nhập bằng email + mật khẩu hộp thư; backend gọi sang Mail API để xác thực rồi lưu token vào DB và gán `user_id` vào session cookie.

### 3.1 Luồng đăng nhập

1. Client gọi `POST /api/v1/auth/connect` với `email`, `password`, `label` (ví dụ `INBOX`).
2. `MailApiService.login()` gọi `POST {MAIL_API_BASE_URL}/api/auth/token` kèm header `X-Mail-Api-Token`.
3. Mail API trả về `{accessToken, refreshToken, tokenId, accessTokenTtl, refreshExpiresAt}`.
4. `AuthService.store_tokens()` upsert bản ghi `users` và `oauth_tokens`.
5. Gán `request.session["user_id"]`, `request.session["user_email"]` → cookie session được ký và trả về trình duyệt.

### 3.2 Kiểm tra trạng thái

- `GET /api/v1/auth/status` đọc `request.session.get("user_id")`.
- `POST /api/v1/auth/disconnect` xóa token và hủy session.

### 3.3 Dependency

```python
# app/core/dependencies.py
def get_current_user_dependency(request: Request) -> int:
    """Bắt buộc đã đăng nhập, ném 401 nếu không có session."""

def get_optional_user_dependency(request: Request) -> int | None:
    """Trả None nếu chưa đăng nhập (dùng cho endpoint cho phép cả khách)."""
```

### 3.4 Bảo mật session

- Cookie được ký bằng `SECRET_KEY` (không mã hóa nội dung, chỉ chống giả mạo).
- `HttpOnly` + `SameSite=Lax` để hạn chế XSS/CSRF.
- `Secure=true` được bật khi chạy HTTPS production.

---

## 4. Cơ sở dữ liệu

SQLite đặt tại `data/app.db`. Toàn bộ model nằm ở [app/models/](../app/models/).

### 4.1 `users`
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INTEGER PK | Auto-increment |
| email | TEXT UNIQUE | Email người dùng |
| created_at | TIMESTAMP | Tạo ở UTC |
| last_login | TIMESTAMP | Cập nhật mỗi lần login |
| last_fetch_at | TIMESTAMP | Lần fetch email gần nhất |
| last_analysis_at | TIMESTAMP | Lần phân tích gần nhất |

### 4.2 `oauth_tokens`
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id | |
| token | TEXT | JSON blob: `{access_token, token_type, token_id, refresh_expires_at}` |
| refresh_token | TEXT | Opaque token từ Mail API |
| expires_at | TIMESTAMP | Khi `access_token` hết hạn |
| created_at, updated_at | TIMESTAMP | |

### 4.3 `emails`
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| gmail_message_id | TEXT | UID lấy từ Mail API |
| subject, sender, recipient | TEXT | |
| body | TEXT | Raw HTML/plain |
| received_at | TIMESTAMP | Từ header email |
| fetched_at | TIMESTAMP | Thời điểm đưa vào DB |
| created_at | TIMESTAMP | |

Ràng buộc: `UNIQUE(user_id, gmail_message_id)` để chống trùng.

### 4.4 `predictions`
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INTEGER PK | |
| email_id | INTEGER FK | |
| prediction | INTEGER | 0 = benign, 1 = phishing |
| probability | REAL | Xác suất trực tiếp từ model |
| ensemble_score | REAL | Điểm tổng hợp model + feature risk |
| classification | TEXT | `LEGITIMATE` \| `SUSPICIOUS` \| `PHISHING` |
| threshold | REAL | Ngưỡng quyết định |
| suspicious_margin | REAL | Khoảng tới mức PHISHING |
| model_version | TEXT | Phiên bản model |
| input_source | TEXT | `original` hoặc `translated_body` |
| created_at | TIMESTAMP | |

### 4.5 `prediction_features`
Ghi lại feature trích xuất khi phân tích: `links_count`, `has_attachment`, `urgent_keywords`, `sender_domain`, `sender_risk` (`TRUSTED` / `UNKNOWN` / `SUSPICIOUS` / `HIGH_RISK`).

> `has_attachment` được tính từ `EmailAttachment.count_by_email_id(email_id)` (không còn stub `0`). `sender_risk` đọc từ `formula_details["domain"]["domain_type"]`.

### 4.6 `prediction_links`
Chi tiết từng URL trong email: `url`, `domain`, `link_type`, `risk_score`.

### 4.7 `suspicious_segments`
Đoạn văn bản nghi ngờ: `text`, `score`, `severity` (`HIGH` / `MEDIUM` / `LOW`), `reasons` (CSV).

### 4.8 `vt_link_checks`
Kết quả quét VirusTotal: `url`, `url_hash` (SHA256), `status` (`pending_scan` / `success` / `error`), bốn chỉ số `malicious` / `suspicious` / `harmless` / `undetected`, `last_checked_at`, `error_message`. `UNIQUE(email_id, url_hash)`.

### 4.9 `email_attachments`
Mỗi attachment fetch về từ Mail API tạo một row.

| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INTEGER PK | |
| email_id | INTEGER FK → emails.id | |
| filename | TEXT | Lấy từ header `Content-Disposition` |
| mime_type | TEXT | `application/pdf`, `image/png`, … |
| size | INTEGER | Bytes thực tế (0 nếu chưa có blob) |
| sha256 | TEXT | Hash của bytes (hoặc surrogate hash khi mail-api không trả nội dung) |
| storage_path | TEXT NULLABLE | Đường dẫn tuyệt đối tới blob trên đĩa; `NULL` nếu chỉ có metadata |
| created_at | TIMESTAMP | |

Ràng buộc: `UNIQUE(email_id, sha256)` để dedupe khi cùng file đính kèm xuất hiện nhiều lần. Blob lưu tại `${ATTACHMENT_DIR}/${email_id}/${sha256}${ext}`.

### 4.10 `vt_attachment_checks`
Verdict VirusTotal cho từng attachment.

| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INTEGER PK | |
| user_id | INTEGER FK → users.id | |
| email_id | INTEGER FK → emails.id | |
| attachment_id | INTEGER FK → email_attachments.id | UNIQUE — mỗi attachment có 1 row scan |
| sha256 | TEXT | Hash dùng để query VT |
| status | TEXT | `pending_scan` / `success` / `error` |
| malicious / suspicious / harmless / undetected | INTEGER | `last_analysis_stats` từ VT |
| last_checked_at | TIMESTAMP | |
| error_message | TEXT NULLABLE | Lưu lý do khi `status='error'` (file > 32 MB, thiếu blob, lỗi HTTP, …) |

### 4.11 `vt_scan_logs`, `fetch_logs`, `analysis_logs`, `translation_logs`, `vt_daily_usage`
Các bảng log cho từng loại tác vụ. Mỗi bản ghi chứa thời điểm, nguồn kích hoạt (`scheduler`, `scheduler-attachments`, hoặc `manual`), số lượng bản ghi xử lý và cột đặc thù (ví dụ `quota_remaining`, `chunk_count`, `duration_ms`). Job attachment scan dùng `source='scheduler-attachments'` để phân biệt với link scan.

---

## 5. Pydantic schema

### 5.1 `auth.py`
- `MailConnect`: `{email, password, label?}`
- `AuthStatus`: `{authenticated, user_id?, user_email?}`

### 5.2 `prediction.py`
- `PredictionRequest`: `{email_text, subject?, has_attachment?, links_count?, sender_domain?, urgent_keywords?}`
- `PredictionResponse`: `{prediction, classification, probability, ensemble_score, threshold, suspicious_margin, email_id?, is_phishing, features?, formula_details?}`
- `TranslatedEmailAnalysisRequest`: `{translated_text}`

### 5.3 `email.py`
- `EmailFetchRequest`: `{max_results: int (1..500)}`
- `EmailFetchResponse`: `{count, emails}`
- `EmailListResponse`: `{emails, limit, offset}`
- `EmailDetail`: tổng hợp email + prediction + VT links.

### 5.4 `translation.py`
- `TranslateTextRequest`: `{text: str (1..120_000)}`

### 5.5 `history.py`, `common.py`
Định nghĩa `PaginationParams`, `ErrorResponse`, `HistoryPredictionItem`, `HistoryEmailItem`, `LogItem`…

---

## 6. Services

Nằm ở [app/services/](../app/services/).

### 6.1 `auth_service.py`
- `store_tokens(...)` — Pack `access_token` + metadata thành JSON, lưu `refresh_token` riêng.
- `get_tokens(user_id)` — Deserialize và trả dict đầy đủ.
- `has_refresh_token(user_id)` — Kiểm tra khả năng refresh.
- `delete_tokens(user_id)` — Xóa token khi logout.

### 6.2 `mail_api_service.py`
Tích hợp Mail API tại `MAIL_API_BASE_URL`. Mọi request có header `X-Mail-Api-Token` (app-level) và `X-Mail-Access-Token` (user-level, khi cần).
- `login(email, password, label)` → `/api/auth/token`
- `refresh(user_id)` → `/api/auth/refresh`
- `revoke(user_id)` → `/api/auth/revoke`
- `fetch_emails(user_id, max_results)` gọi `/api/mail/list` lấy UID, sau đó gọi `/api/mail/message`. Trả thêm `attachments[]` (xem `_parse_attachments`) và field `uid` để service tầng trên có thể follow-up download blob.
- `fetch_message(user_id, message_uid)` — fetch lại một message cụ thể bằng UID (`POST /api/mail/message`), dùng cho tính năng reload attachment.
- `fetch_attachment_content(user_id, message_uid, attachment_index, filename?)` — POST `/api/mail/attachment` để lấy bytes khi mail-api không inline base64 trong response message. Mail API hiện dùng `attachmentIndex` 0-based thay vì attachment id riêng.

Nếu access token hết hạn, service tự refresh qua `refresh_token`. Parser dùng nhiều khoá để tương thích nhiều shape khác nhau (`content` / `contentBase64` / `data` / `base64` cho inline). Attachment blob được fetch theo `attachment_index` 0-based vì mail-api không expose attachment id riêng.

### 6.3 `prediction_service.py`
- `_load_model()` — Lazy load pipeline từ `MODEL_PATH`, đọc metadata (`threshold`, `suspicious_margin`, `feature_cols`).
- `predict(email_text, …)` — Luồng: chuẩn hoá text → trích xuất feature → `model.predict_proba` → tính `ensemble_score` → `_classify_threat_level` → trả kết quả đầy đủ (kèm `formula_details` và `suspicious_segments`).
- Phân loại: `LEGITIMATE` khi `ensemble_score < threshold`; `SUSPICIOUS` khi `threshold ≤ score < threshold + margin`; `PHISHING` khi `score ≥ threshold + margin`.

### 6.4 `email_service.py`
- `create_email(...)` — Upsert theo `gmail_message_id`.
- `get_email_by_id()`, `get_emails_by_user()`, `get_email_with_prediction()`.
- `create_prediction(...)` — Lưu `predictions` kèm features/links/segments trong một transaction. `sender_risk` đọc từ `formula_details["domain"]["domain_type"]` (trước đó dùng key `sender_classification` không tồn tại nên luôn ra `UNKNOWN`).
- `analyze_and_save(email_id, email_text)` — Đọc envelope `sender` của email từ DB, regex domain rồi truyền vào `PredictionService.predict()` cùng `has_attachment` (lấy từ `EmailAttachment.count_by_email_id`). Trước đó scheduler scrape body để lấy domain → kết quả thiếu chính xác và `TRUSTED_DOMAINS` không kích hoạt được vì domain trong body khác domain From.

### 6.4b `attachment_service.py`
Persist attachment lên đĩa + DB. API:
- `persist_for_email(user_id, email_id, message_uid, attachments)` — duyệt list trả về từ `mail_api_service._parse_attachments`. Nếu không có inline base64, fallback `MailApiService.fetch_attachment_content`.
- `reload_for_email(user_id, email)` — fetch lại message từ Mail API theo `emails.gmail_message_id` (UID), parse lại `attachments[]`, persist blob/metadata, rồi xoá placeholder metadata-only trùng `filename + mime_type + size` nếu blob thật đã được tải về.
- Bytes được hash SHA-256 rồi ghi vào `${ATTACHMENT_DIR}/${email_id}/${sha256}${ext}`. Cùng SHA giữa các email khác nhau ⇒ ghi vào thư mục riêng từng email (không share blob giữa user khác nhau).
- Khi không lấy được bytes, ghi metadata-only với `storage_path = NULL` và `sha256 = surrogate(filename:mime:size:uid)` để hàng UI vẫn thấy attachment tồn tại nhưng VT scan sẽ skip.
- File > `ATTACHMENT_MAX_SIZE_BYTES` cũng store metadata-only (VT free tier không upload nổi).

### 6.5 `virustotal_service.py`
- `get_daily_usage()` trả `{date, used, limit, remaining}` đọc từ `vt_daily_usage`. Quota chia chung giữa **link scan** và **file scan**.
- `scan_user_email_links(user_id)` — Duyệt email của user, trích URL từ body, hỏi VT:
  - `GET /api/v3/urls/{url_id}` → nếu đã có report, cập nhật counters.
  - Nếu 404, `POST /api/v3/urls` để queue.
  - Mỗi URL tạo/ cập nhật `vt_link_checks` và ghi tăng `vt_daily_usage`.
- `scan_user_email_attachments(user_id)` / `scan_single_email_attachments(user_id, email_id)`:
  - Lấy attachment chưa scan thành công (`EmailAttachment.get_unscanned_for_user`).
  - `GET /api/v3/files/{sha256}` trước (1 quota). 200 ⇒ lưu verdict.
  - 404 ⇒ nếu attachment đang `pending_scan`, giữ nguyên pending và không upload lại file. Nếu chưa từng pending, file ≤ 32 MB và có blob thì `POST /api/v3/files` (multipart upload, +1 quota) rồi đánh `pending_scan`.
  - File quá lớn / không có blob ⇒ ghi `status='error'` kèm `error_message` để UI hiển thị.
- `refresh_pending_email_attachments(user_id, email_id)` — chỉ xử lý attachment đang `pending_scan` của một email: lookup lại `GET /api/v3/files/{sha256}` để cập nhật `success` nếu VT đã có report, không upload lại file.
- Nếu `used ≥ VIRUSTOTAL_DAILY_LIMIT` thì service thoát sớm để tránh vượt hạn mức.

### 6.6 `translation_service.py`
- Sử dụng Gemini (`GEMINI_TRANSLATION_MODEL`) qua endpoint `generateContent`.
- `translate_to_english(text, user_id?, email_id?)`:
  1. Cắt text thành chunk ≤ `TRANSLATION_CHUNK_MAX_CHARS`.
  2. Thay URL bằng placeholder để tránh bị "dịch sai" → gọi Gemini → thay lại URL gốc.
  3. Ghi nhật ký vào `translation_logs`: chunk_count, duration_ms, urls_preserved, translated_text.
- Hỗ trợ multi-key (`GOOGLE_AI_API_KEYS`) để failover khi 1 key bị rate limit.

### 6.7 `scheduler_service.py`
Dùng APScheduler, chạy 3 job định kỳ mỗi 5 phút:
- `fetch_new_emails_for_all_users()` — Với mỗi user có `refresh_token`, kéo tối đa 50 email mới, lưu `fetch_logs`. Khi email là **mới** (insert thành công), gọi `AttachmentService.persist_for_email` để lưu blob + metadata; email đã tồn tại bỏ qua để không re-download.
- `analyze_unanalyzed_emails_for_all_users()` — Lấy các email chưa có `predictions`, phân tích tối đa 20 email/user, ghi `analysis_logs`.
- `scan_links_with_virustotal_for_all_users()` — Lần lượt gọi `VirusTotalService.scan_user_email_links()` rồi `scan_user_email_attachments()` (cùng quota). Ghi 2 row `vt_scan_logs` riêng (`source='scheduler'` cho link, `source='scheduler-attachments'` cho file). Link scan chạy trước để URL không bị file upload đốt hết quota.

### 6.8 `stats_service.py`
Chịu trách nhiệm tính toán tất cả số liệu dashboard:
- `get_overview(user_id)` — trả thêm block `attachments: {total, scanned, malicious, suspicious, pending}` từ `VTAttachmentCheck.get_user_overview`.
- Block `virustotal` và endpoint `/stats/links` lấy từ `vt_link_checks`: `total_links`, `scanned_links`, `malicious_links`, `suspicious_links`, `clean_links`, `pending_links`, `error_links`, vote totals. Không lấy từ `prediction_links` vì `prediction_links` là output ML feature/risk, không phải verdict VT.
- `get_threat_trend(user_id, days)`
- `get_classification_breakdown(user_id)`
- `get_top_senders / get_top_domains`
- `get_feature_stats`, `get_suspicious_segments_stats`
- `get_vt_link_stats(user_id, top_n)`
- `get_email_timeline(user_id, days)`
- `get_probability_distribution(user_id)`

> Tất cả query stats đi qua CTE `latest_preds` trong [`app/models/stats.py`](../app/models/stats.py). CTE đã được cập nhật để **bỏ qua `input_source='translated_body'`** — trùng tiêu chí với inbox view (`Prediction.get_latest_original_by_email_id`) nên dashboard không còn bị "đảo lớp" khi cùng 1 email có cả prediction original lẫn translated.

---

## 7. API endpoints (v1)

Prefix chung: `/api/v1`.

### 7.1 `/auth`

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| POST | `/auth/connect` | — | Đăng nhập bằng email/password, trả `{user_id, user_email}` |
| GET | `/auth/status` | — | Trả `AuthStatus` |
| POST | `/auth/disconnect` | Yes | Đăng xuất, xóa token |

### 7.2 `/emails`

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| POST | `/emails/fetch` | Yes | Kéo email mới từ Mail API (đồng thời lưu attachment) |
| GET | `/emails/list` | Yes | Danh sách email (phân trang) — kèm `attachment_summary` per row |
| GET | `/emails/{email_id}` | Yes | Chi tiết email |
| GET | `/emails/{email_id}/attachments` | Yes | List attachment + verdict VT cho từng file |
| POST | `/emails/{email_id}/attachments/reload` | Yes | Tải lại attachment từ Mail API theo UID message, lưu blob còn thiếu và xoá placeholder metadata-only đã được thay thế |
| POST | `/emails/{email_id}/attachments/scan` | Yes | Trigger thủ công VT scan cho attachment của email |
| POST | `/emails/{email_id}/attachments/refresh-pending` | Yes | Lookup lại report VT cho attachment đang `pending_scan`, không upload lại file |
| GET | `/emails/count` | Yes | Tổng email của user |

### 7.3 `/predictions`

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| POST | `/predictions/analyze` | Optional | Phân tích text tự do |
| POST | `/predictions/analyze-email/{email_id}` | Yes | Phân tích email đã lưu |
| POST | `/predictions/analyze-translated/{email_id}` | Yes | Phân tích bản dịch |
| GET | `/predictions/{email_id}/details` | Yes | Lấy prediction + features + links + segments |

### 7.4 `/history`

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| GET | `/history/predictions` | Yes | Lịch sử dự đoán |
| GET | `/history/emails` | Yes | Lịch sử email |
| GET | `/history/analysis-logs` | Yes | Log phân tích |
| GET | `/history/fetch-logs` | Yes | Log fetch |
| GET | `/history/vt-scan-logs` | Yes | Log quét VirusTotal |

### 7.5 `/translate`

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| POST | `/translate/text` | Yes | Dịch text đầu vào sang tiếng Anh |
| GET | `/translate/{email_id}` | Yes | Dịch body email trong DB |
| GET | `/translate/status` | Yes | Thống kê dịch: success, failure, chunk |
| GET | `/translate/history` | Yes | Danh sách `translation_logs` |

### 7.6 `/stats`

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| GET | `/stats/overview` | Yes | Thống kê tổng quan |
| GET | `/stats/trend?days=` | Yes | Xu hướng theo ngày |
| GET | `/stats/classification` | Yes | Tỉ lệ 3 nhóm |
| GET | `/stats/top-senders?limit=` | Yes | Top người gửi theo threat |
| GET | `/stats/top-domains?limit=` | Yes | Top domain gửi |
| GET | `/stats/features` | Yes | Thống kê feature |
| GET | `/stats/segments` | Yes | Tỉ lệ severity đoạn nghi ngờ |
| GET | `/stats/links?top_n=` | Yes | Top URL VirusTotal đánh dấu |
| GET | `/stats/timeline?days=` | Yes | Khối lượng email theo ngày |
| GET | `/stats/probability-dist` | Yes | Histogram xác suất |

---

## 8. Luồng xử lý đầu–cuối

### 8.1 Đăng nhập → fetch → phân tích

```
1. Client: POST /auth/connect (email, password)
     → MailApiService.login() → OAuthToken lưu DB
     → request.session["user_id"] = id
2. Client: POST /emails/fetch (max_results=50)
     → MailApiService.fetch_emails()        (parse attachments[] kèm)
     → EmailService.create_email()  × N
     → AttachmentService.persist_for_email() (chỉ cho email mới)
     → FetchLog
3. Scheduler (mỗi 5 phút):
     fetch_new_emails_for_all_users()       (+ persist attachment cho email mới)
     analyze_unanalyzed_emails_for_all_users()
       → PredictionService.predict(sender_domain=envelope-from, has_attachment=count)
       → EmailService.create_prediction()
     scan_links_with_virustotal_for_all_users()
       → VirusTotalService.scan_user_email_links()
       → VirusTotalService.scan_user_email_attachments()
       → VTScanLog × 2 (links + attachments) / VTLinkCheck / VTAttachmentCheck
4. Client: GET /stats/overview
     → StatsService.get_overview(user_id)   (kèm block attachments)
```

### 8.2 Phân tích văn bản tự do

```
Client → POST /predictions/analyze (email_text)
       → PredictionService.predict()
       → Response {prediction, classification, probability, ensemble_score,
                    formula_details, features, suspicious_segments}
```

### 8.3 Dịch + phân tích bản dịch

```
Client → POST /translate/text              # Gemini trả translated_text
Client → POST /predictions/analyze-translated/{email_id}
         body: { translated_text }
       → PredictionService.predict(email_text=translated_text, ...)
       → input_source = "translated_body"
```

---

## 9. Tích hợp bên ngoài

### 9.1 Mail API
- Base URL: biến `MAIL_API_BASE_URL` (mặc định `http://localhost:8095`).
- Header chung: `X-Mail-Api-Token`, `Content-Type: application/json`.
- Endpoint sử dụng: `/api/auth/token`, `/api/auth/refresh`, `/api/auth/revoke`, `/api/mail/list`, `/api/mail/message`.

### 9.2 VirusTotal v3
- Base: `https://www.virustotal.com/api/v3`.
- Header: `x-apikey: VIRUSTOTAL_API_KEY`.
- Endpoint dùng:
  - URL: `GET /urls/{url_id}`, `POST /urls`.
  - File: `GET /files/{sha256}`, `POST /files` (multipart, ≤ 32 MB cho free tier).
- Response chuẩn: `data.attributes.last_analysis_stats.{malicious, suspicious, harmless, undetected}`.
- Quota hàng ngày tracked trong `vt_daily_usage` (chia chung cho cả URL lẫn file). Job link scan chạy trước file scan để URL có cơ hội cover trước khi file upload đốt quota.

### 9.3 Google Gemini
- Base: `https://generativelanguage.googleapis.com/v1beta`.
- Model mặc định: `gemini-3-flash-preview`.
- Auth: header `x-goog-api-key` hoặc query `?key=`.
- Endpoint: `POST /models/{model}:generateContent`.
- Hỗ trợ multiple keys failover.

---

## 10. Logging & quan sát

- [app/utils/logger.py](../app/utils/logger.py) cấu hình `RotatingFileHandler` (10 MB, 5 bản) + console.
- Log level đọc từ biến `LOG_LEVEL` (mặc định `INFO`).
- Mỗi request được gán `request_id` (UUID) qua middleware và ghi kèm `method`, `path`, `user_id`, `status_code`, `duration_ms`.
- Các service ghi log quan trọng (login, fetch, predict, VT scan, translate) để phục vụ điều tra.

---

## 11. Chạy backend

```bash
# Cài dependency
pip install -r requirements.txt

# Khởi tạo DB (tạo bảng nếu chưa có)
python run.py --init-db

# Chạy dev
uvicorn app.main:app --reload --port 5000
```

Các biến môi trường bắt buộc: `SECRET_KEY`, `MAIL_API_TOKEN`, `VIRUSTOTAL_API_KEY`, `GOOGLE_AI_API_KEY`. Khi triển khai production, bật `SESSION_COOKIE_SECURE=true` và đảm bảo cấu hình `CORS_ORIGINS` đúng với origin của frontend.

---

## 12. Chi tiết triển khai

Phần này đi sâu vào middleware stack, dependency injection, ví dụ JSON đầy đủ và các thuật toán đặc thù. Luồng tuần tự của từng tính năng xem [SEQUENCE_DIAGRAMS.md](./SEQUENCE_DIAGRAMS.md).

### 12.1 Middleware stack

`app/main.py` lắp các middleware theo thứ tự:

```python
app = FastAPI(
    title="PhishGuard API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# 1. CORS — cho phép frontend gọi cross-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Session — ký cookie bằng SECRET_KEY
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="session",
    https_only=settings.SESSION_COOKIE_SECURE,
    same_site=settings.SESSION_COOKIE_SAMESITE,
)

# 3. Request ID + logger
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled", extra={"request_id": request_id})
        raise
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": request.session.get("user_id"),
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response
```

### 12.2 Startup / shutdown hook

```python
@app.on_event("startup")
async def startup_event():
    await init_database()                  # Tạo bảng nếu chưa có
    prediction_service.load_model()        # Nạp pipeline XGBoost
    scheduler_service.start()              # APScheduler: 3 job /5 phút

@app.on_event("shutdown")
async def shutdown_event():
    scheduler_service.stop()
    await close_database()
```

### 12.3 Dependency injection

```python
# app/core/dependencies.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

def get_current_user_dependency(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id

def get_optional_user_dependency(request: Request) -> int | None:
    return request.session.get("user_id")

CurrentUserId  = Annotated[int, Depends(get_current_user_dependency)]
OptionalUserId = Annotated[int | None, Depends(get_optional_user_dependency)]
DbSession      = Annotated[AsyncSession, Depends(get_db)]
```

Trong endpoint:

```python
@router.get("/overview")
async def get_overview(user_id: CurrentUserId, db: DbSession):
    return await stats_service.get_overview(db, user_id)
```

### 12.4 Format phản hồi lỗi thống nhất

```python
# app/utils/api_response.py
class ApiError(BaseModel):
    detail: str
    code: str
    request_id: str | None = None

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiError(
            detail=exc.detail,
            code=_http_code_to_name(exc.status_code),
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )
```

Ví dụ response 401:
```json
{
  "detail": "Not authenticated",
  "code": "UNAUTHORIZED",
  "request_id": "b9c3e0d0-0a1d-4c1b-9a6c-0b1dc0aefb1a"
}
```

### 12.5 `MailApiService` — chi tiết login + refresh

```python
class MailApiService:
    def __init__(self, settings: Settings):
        self.base_url   = settings.MAIL_API_BASE_URL
        self.app_token  = settings.MAIL_API_TOKEN
        self.client     = httpx.AsyncClient(timeout=15.0)

    async def login(self, email: str, password: str, label: str = "INBOX"):
        resp = await self.client.post(
            f"{self.base_url}/api/auth/token",
            headers={"X-Mail-Api-Token": self.app_token},
            json={"email": email, "password": password, "label": label},
        )
        if resp.status_code in (401, 403):
            raise HTTPException(401, "Mail credentials rejected")
        resp.raise_for_status()
        return resp.json()   # {accessToken, refreshToken, tokenId, ...}

    async def _ensure_access_token(self, db, user_id: int) -> str:
        tokens = await auth_service.get_tokens(db, user_id)
        if tokens["expires_at"] > datetime.utcnow():
            return tokens["access_token"]
        # Hết hạn -> refresh
        refreshed = await self._refresh(tokens["refresh_token"])
        await auth_service.update_access_token(db, user_id, refreshed)
        return refreshed["accessToken"]
```

### 12.6 `PredictionService.predict` — chi tiết

```python
def predict(
    self,
    email_text: str,
    subject: str | None = None,
    has_attachment: int | None = None,
    links_count: int | None = None,
    sender_domain: str | None = None,
    urgent_keywords: int | None = None,
) -> dict:
    text = normalize_text(email_text)

    feats = {
        "text":              text,
        "has_attachment":    has_attachment if has_attachment is not None
                              else detect_attachment_mention(text),
        "links_count":       links_count if links_count is not None
                              else count_urls(text),
        "urgent_keywords":   urgent_keywords if urgent_keywords is not None
                              else detect_urgent_keywords(text),
        "body_length":       len(text),
        "exclamation_count": exclamation_count(text),
        "sender_domain":     sender_domain or extract_sender_domain(text) or "unknown",
    }

    X     = pd.DataFrame([feats], columns=self.feature_cols)
    proba = float(self.model.predict_proba(X)[0, 1])

    link_domains = extract_link_domains(text)
    link_risk    = self._aggregate_link_risk(link_domains)
    domain_risk  = self._sender_domain_risk(feats["sender_domain"])

    ensemble = (
        0.55 * proba
        + 0.20 * float(feats["urgent_keywords"])
        + 0.15 * link_risk
        + 0.10 * domain_risk
    )
    classification = self._classify_threat_level(ensemble)

    return {
        "prediction":        int(proba >= self.threshold),
        "classification":    classification,
        "probability":       proba,
        "ensemble_score":    ensemble,
        "threshold":         self.threshold,
        "suspicious_margin": self.suspicious_margin,
        "is_phishing":       classification == "PHISHING",
        "features":          feats,
        "formula_details": {
            "model_component":  0.55 * proba,
            "urgent_component": 0.20 * float(feats["urgent_keywords"]),
            "links_component":  0.15 * link_risk,
            "domain_component": 0.10 * domain_risk,
        },
        "suspicious_segments": self._extract_segments(email_text),
    }
```

### 12.7 `VirusTotalService.scan_user_email_links` — edge case

```python
async def scan_user_email_links(self, db, user_id: int) -> dict:
    usage = await self.get_daily_usage(db)
    if usage["used"] >= self.daily_limit:
        return {"checked": 0, "skipped": 0, "errors": 0,
                "quota_remaining": 0, "reason": "quota_exceeded"}

    urls = await self._collect_unscanned_urls(db, user_id)
    checked = skipped = errors = 0

    for url in urls:
        if usage["used"] >= self.daily_limit:
            skipped += 1
            continue

        url_id = base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()
        r = await self.client.get(
            f"{self.base_url}/urls/{url_id}",
            headers={"x-apikey": self.api_key},
        )

        if r.status_code == 200:
            stats = r.json()["data"]["attributes"]["stats"]
            await self._upsert_link(db, user_id, url, "success", stats)
            checked += 1
        elif r.status_code == 404:
            submit = await self.client.post(
                f"{self.base_url}/urls",
                headers={"x-apikey": self.api_key},
                data={"url": url},
            )
            if submit.status_code == 200:
                await self._upsert_link(db, user_id, url, "pending_scan", None)
            else:
                errors += 1
        elif r.status_code == 429:
            # Rate limit -> dừng, job sau sẽ chạy tiếp
            break
        else:
            await self._upsert_link(db, user_id, url, "error",
                                    error=r.text[:500])
            errors += 1

        usage["used"] += 1
        await self._incr_daily_usage(db)

    quota_remaining = self.daily_limit - usage["used"]
    await self._log_scan(db, user_id, "scheduler", checked, skipped, errors, quota_remaining)
    return {"checked": checked, "skipped": skipped, "errors": errors,
            "quota_remaining": quota_remaining}
```

### 12.8 `TranslationService` — URL masking và chunking

```python
URL_RE = re.compile(r"https?://\S+")

def translate_to_english(self, text: str, user_id=None, email_id=None) -> dict:
    if len(text) > self.max_input_chars:
        raise HTTPException(413, "Text too long")

    masked, urls = self._mask_urls(text)
    chunks = self._split_chunks(masked, self.chunk_max_chars)

    t0 = time.monotonic()
    translated_parts = []
    for i, chunk in enumerate(chunks):
        part = self._call_gemini(chunk)
        translated_parts.append(part)
        if i < len(chunks) - 1:
            time.sleep(0.25)               # throttle
    translated = self._unmask_urls("".join(translated_parts), urls)

    duration = int((time.monotonic() - t0) * 1000)
    self._log_translation(user_id, email_id, len(text), len(translated),
                          len(chunks), len(urls), duration, translated)

    return {
        "translated_text": translated,
        "chunk_count":     len(chunks),
        "duration_ms":     duration,
        "urls_preserved":  len(urls),
    }

def _mask_urls(self, text: str):
    urls = []
    def _sub(m):
        urls.append(m.group(0))
        return f"__URL_{len(urls) - 1}__"
    return URL_RE.sub(_sub, text), urls

def _unmask_urls(self, text: str, urls: list[str]) -> str:
    for i, url in enumerate(urls):
        text = text.replace(f"__URL_{i}__", url)
    return text
```

Multi-key failover khi Gemini trả 429 hoặc 5xx:

```python
def _call_gemini(self, prompt: str) -> str:
    last_err = None
    for key in self.api_keys:
        try:
            r = self._call_once(prompt, key)
            return r
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503):
                last_err = e
                continue
            raise
    raise HTTPException(502, f"Gemini unavailable: {last_err}")
```

### 12.9 `SchedulerService` — APScheduler

```python
class SchedulerService:
    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self):
        self._scheduler.add_job(self.fetch_new_emails_for_all_users,
                                IntervalTrigger(minutes=5),
                                id="fetch", replace_existing=True)
        self._scheduler.add_job(self.analyze_unanalyzed_emails_for_all_users,
                                IntervalTrigger(minutes=5),
                                id="analyze", replace_existing=True)
        self._scheduler.add_job(self.scan_links_with_virustotal_for_all_users,
                                IntervalTrigger(minutes=5),
                                id="vt_scan", replace_existing=True)
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown(wait=False)
```

### 12.10 Ví dụ JSON request/response

**`POST /api/v1/auth/connect`**
```json
// Request
{ "email": "user@example.com", "password": "******", "label": "INBOX" }

// Response 200
{ "user_id": 7, "user_email": "user@example.com" }

// Response 401
{ "detail": "Mail credentials rejected", "code": "UNAUTHORIZED",
  "request_id": "..." }
```

**`POST /api/v1/emails/fetch`**
```json
// Request
{ "max_results": 50 }

// Response
{
  "count": 12,
  "emails": [
    {
      "id": 412,
      "gmail_message_id": "UID-1042",
      "subject": "Your invoice",
      "sender": "billing@example.com",
      "received_at": "2026-04-24T17:12:00Z"
    }
  ]
}
```

**`GET /api/v1/predictions/{email_id}/details`**
```json
{
  "prediction": {
    "id": 201, "email_id": 412, "prediction": 1,
    "classification": "PHISHING", "probability": 0.92,
    "ensemble_score": 0.87, "threshold": 0.6, "suspicious_margin": 0.2,
    "input_source": "original", "model_version": "v1"
  },
  "features": {
    "links_count": 3, "has_attachment": 0, "urgent_keywords": 1,
    "sender_domain": "examp1e.com", "sender_risk": "SUSPICIOUS"
  },
  "links": [
    { "url": "http://short.ly/abc", "domain": "short.ly",
      "link_type": "shortener", "risk_score": 0.6 }
  ],
  "suspicious_segments": [
    { "text": "Please verify within 24h...",
      "score": 84.1, "severity": "HIGH",
      "reasons": ["urgent_keyword","deadline"] }
  ],
  "vt_links": [
    { "url": "http://short.ly/abc", "status": "success",
      "malicious": 4, "suspicious": 2, "harmless": 60, "undetected": 12 }
  ]
}
```

### 12.11 Bảo mật

- **Password không lưu:** Backend chỉ chuyển tiếp tới Mail API, không bao giờ persist mật khẩu vào DB.
- **Session cookie:** Starlette ký JSON bằng `SECRET_KEY` (itsdangerous). Không mã hoá nội dung nên không được lưu dữ liệu nhạy cảm — chỉ giữ `user_id`, `user_email`.
- **CORS whitelist:** Chỉ những origin trong `CORS_ORIGINS` mới được phép; không dùng `*` để tránh rò rỉ cookie.
- **Rate limit ứng dụng:** VirusTotal có quota ngày qua `vt_daily_usage`. Gemini không hard-limit nhưng có `sleep(0.25s)` giữa chunk + failover key.
- **SQL injection:** Sử dụng SQLAlchemy ORM + named params, không concat chuỗi SQL.
- **XSS:** Response trả JSON thuần, không render HTML ở backend (SPA tự escape).

### 12.12 Logging sample

```jsonl
{"ts":"2026-04-25T04:12:01Z","level":"INFO","msg":"request","request_id":"…",
 "method":"POST","path":"/api/v1/predictions/analyze","status":200,
 "duration_ms":218.4,"user_id":7}
{"ts":"2026-04-25T04:12:03Z","level":"INFO","msg":"predict",
 "request_id":"…","user_id":7,"classification":"PHISHING",
 "ensemble_score":0.87,"links":3,"threshold":0.6}
```

### 12.13 Tham chiếu sơ đồ tuần tự

| Luồng | Diagram |
|-------|---------|
| Login | [1](./SEQUENCE_DIAGRAMS.md#1-đăng-nhập-mail-api-connect) |
| Fetch email | [4](./SEQUENCE_DIAGRAMS.md#4-fetch-email-thủ-công), [5](./SEQUENCE_DIAGRAMS.md#5-scheduler--job-fetch-email-định-kỳ) |
| Analyze | [6](./SEQUENCE_DIAGRAMS.md#6-scheduler--job-phân-tích-email-định-kỳ), [8](./SEQUENCE_DIAGRAMS.md#8-phân-tích-email-thủ-công-paste-text) |
| VT scan | [7](./SEQUENCE_DIAGRAMS.md#7-scheduler--job-quét-link-virustotal), [10](./SEQUENCE_DIAGRAMS.md#10-virustotal-url-scan-chi-tiết) |
| Translation | [9](./SEQUENCE_DIAGRAMS.md#9-dịch--phân-tích-bản-dịch) |
| Token refresh | [14](./SEQUENCE_DIAGRAMS.md#14-auto-refresh-token-khi-hết-hạn) |
