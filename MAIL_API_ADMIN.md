# Mail API - Full Admin Flow

Tai lieu nay la full flow de frontend admin implement nhanh: login, refresh token, doc toan bo mail, tai attachment, quan ly thiet bi.

## 1) Muc tieu va kien truc

- Admin doc toan bo mail qua mailbox journal: `archive@spktfpt.online`.
- Mailbox nay duoc feed boi Maddy journal rule (mail in/out copy vao archive).
- Frontend admin goi `mail-api` (khong goi IMAP truc tiep).

Base:

- Base URL: `http://SERVER_IP:8095`
- Header bat buoc cho API app: `X-Mail-Api-Token: <MAIL_API_TOKEN>`
- Swagger UI: `http://SERVER_IP:8095/api-docs`
- OpenAPI JSON: `http://SERVER_IP:8095/openapi.json`

## 2) Prerequisites server

### 2.1 Tao mailbox archive (1 lan)

```bash
docker exec -it maddy maddy creds create archive@spktfpt.online
docker exec -it maddy maddy imap-acct create archive@spktfpt.online
```

### 2.2 Env bat buoc cho token lau dai

- `MAIL_API_TOKEN`
- `JWT_SECRET` (>= 32 ky tu)
- `MAIL_TOKEN_MASTER_KEY` (64 ky tu hex)
- `TOKEN_DB_PATH` (mac dinh `/data/mail_tokens.db`)

Generate:

```bash
openssl rand -base64 48   # JWT_SECRET
openssl rand -hex 32      # MAIL_TOKEN_MASTER_KEY
```

Run:

```bash
docker compose --profile mailapi up -d --build
```

## 3) Full auth flow cho frontend admin

### Step A - Login va tao cap token

`POST /api/auth/token`

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/auth/token" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"archive@spktfpt.online","password":"ARCHIVE_PASSWORD","label":"admin-web"}'
```

Response can luu:

- `accessToken`
- `refreshToken`
- `tokenId`

### Step B - Goi API mail bang access token

Them header:

- `X-Mail-Api-Token: ...`
- `X-Mail-Access-Token: <accessToken>`

### Step C - Refresh khi access het han

Khi API tra `401` do access token expired:

`POST /api/auth/refresh`

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/auth/refresh" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"REFRESH_TOKEN_HIEN_TAI"}'
```

Quan trong:

- Refresh token duoc rotate, phai luu refresh moi.
- Sau refresh thanh cong, retry request truoc do.

### Step D - Logout

Thu hoi refresh token hien tai:

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/auth/revoke" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"REFRESH_TOKEN_HIEN_TAI"}'
```

## 4) Mail flow cho man admin

### 4.1 List mail (archive inbox)

`POST /api/mail/list`

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/mail/list" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "X-Mail-Access-Token: ACCESS_JWT_HERE" \
  -H "Content-Type: application/json" \
  -d '{"folder":"INBOX","limit":30,"offset":0}'
```

List mail co ho tro filter server-side:

- `fromEmail`
- `subjectContains`
- `dateFrom` (ISO datetime)
- `dateTo` (ISO datetime)

Vi du:

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/mail/list" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "X-Mail-Access-Token: ACCESS_JWT_HERE" \
  -H "Content-Type: application/json" \
  -d '{"folder":"INBOX","limit":30,"offset":0,"fromEmail":"alice@example.com","subjectContains":"invoice","dateFrom":"2026-04-01T00:00:00.000Z","dateTo":"2026-04-30T23:59:59.000Z"}'
```

### 4.1.1 List email trong he thong (cho filter dropdown)

`GET /api/system/emails`

```bash
curl -sS "http://SERVER_IP:8095/api/system/emails" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN"
```

### 4.2 Doc chi tiet mail

`POST /api/mail/message`

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/mail/message" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "X-Mail-Access-Token: ACCESS_JWT_HERE" \
  -H "Content-Type: application/json" \
  -d '{"folder":"INBOX","uid":123}'
```

`attachments` trong response co `index`.

### 4.3 Tai attachment

`POST /api/mail/attachment` theo `attachmentIndex`:

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/mail/attachment" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "X-Mail-Access-Token: ACCESS_JWT_HERE" \
  -H "Content-Type: application/json" \
  -d '{"folder":"INBOX","uid":123,"attachmentIndex":0}' \
  --output attachment.bin
```

## 5) Device/token management (admin screen)

### 5.1 Liet ke token thiet bi cua mailbox

`POST /api/auth/tokens/list`

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/auth/tokens/list" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"archive@spktfpt.online","password":"ARCHIVE_PASSWORD"}'
```

### 5.2 Revoke theo tokenId

`POST /api/auth/revoke-by-id`

```bash
curl -sS -X POST "http://SERVER_IP:8095/api/auth/revoke-by-id" \
  -H "X-Mail-Api-Token: YOUR_MAIL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tokenId":"uuid-here"}'
```

## 6) Frontend state machine de implement

- `idle`
- `authenticating`
- `authenticated`
- `refreshing`
- `session_expired`
- `error`

Behavior khuyen nghi:

- Interceptor bat `401` -> lock refresh 1 lan -> retry queue.
- Neu refresh fail -> clear token + redirect login.

## 7) Bao mat production

- Chi mo cong `8095` noi bo hoac sau reverse proxy HTTPS.
- `MAIL_API_TOKEN` la app secret, khong hard-code trong frontend public.
- Backup:
  - `mail-api/data/`
  - `MAIL_TOKEN_MASTER_KEY`
- Mat `MAIL_TOKEN_MASTER_KEY` => khong giai ma duoc password mailbox da luu.

## 8) API contract chi tiet (de frontend implement)

### 8.1 Header convention

- Luon gui: `X-Mail-Api-Token: <MAIL_API_TOKEN>`
- Mailbox auth (chon 1):
  - `X-Mail-Access-Token: <accessToken>` (khuyen dung)
  - hoac `X-Mail-Session: <sessionToken>`
  - hoac body `email` + `password`

### 8.2 JSON response format (chuan moi)

Tat ca API JSON deu theo format:

```json
{
  "error_code": 0,
  "message": "OK",
  "data": {}
}
```

Quy uoc:

- `error_code = 0`: thanh cong
- `error_code != 0`: co loi
- `message`: mo ta ngan gon
- `data`: payload (co the `null`)

Ngoai le:

- `POST /api/mail/attachment` thanh cong se tra binary stream (khong tra JSON).

### 8.3 Error response format

```json
{
  "error_code": 40101,
  "message": "Unauthorized",
  "data": null
}
```

### 8.4 Status code mapping nhanh

- `200`: thanh cong
- `400`: payload thieu/sai
- `401`: unauthorized / token het han / login fail
- `502`: loi IMAP/attachment fetch
- `503`: chua cau hinh token persistent (`JWT_SECRET`, `MAIL_TOKEN_MASTER_KEY`)

## 9) Request/Response mau tung endpoint

### `POST /api/auth/token`

Request:

```json
{
  "email": "archive@spktfpt.online",
  "password": "ARCHIVE_PASSWORD",
  "label": "admin-web"
}
```

Response:

```json
{
  "error_code": 0,
  "message": "Token issued",
  "data": {
    "tokenId": "uuid",
    "accessToken": "jwt",
    "refreshToken": "opaque_refresh_token",
    "accessTokenTtl": "7d",
    "refreshExpiresAt": "2026-07-01T12:00:00.000Z"
  }
}
```

### `POST /api/auth/refresh`

Request:

```json
{
  "refreshToken": "old_refresh_token"
}
```

Response:

```json
{
  "error_code": 0,
  "message": "Token refreshed",
  "data": {
    "tokenId": "uuid",
    "accessToken": "new_jwt",
    "refreshToken": "new_refresh_token",
    "accessTokenTtl": "7d",
    "refreshExpiresAt": "2026-07-01T12:00:00.000Z"
  }
}
```

### `POST /api/mail/list`

Request:

```json
{
  "folder": "INBOX",
  "limit": 30,
  "offset": 0,
  "fromEmail": "alice@example.com",
  "subjectContains": "invoice",
  "dateFrom": "2026-04-01T00:00:00.000Z",
  "dateTo": "2026-04-30T23:59:59.000Z"
}
```

Response:

```json
{
  "error_code": 0,
  "message": "OK",
  "data": {
    "folder": "INBOX",
    "totalFetched": 2,
    "messages": [
      {
        "uid": 345,
        "subject": "Hello",
        "from": {
          "name": "Alice",
          "address": "alice@example.com"
        },
        "date": "2026-04-13T10:00:00.000Z",
        "flags": ["\\Seen"]
      }
    ]
  }
}
```

### `GET /api/system/emails`

Response:

```json
{
  "error_code": 0,
  "message": "OK",
  "data": {
    "emails": [
      "archive@spktfpt.online",
      "user@spktfpt.online"
    ],
    "count": 2
  }
}
```

### `POST /api/mail/message`

Request:

```json
{
  "folder": "INBOX",
  "uid": 345
}
```

Response:

```json
{
  "error_code": 0,
  "message": "OK",
  "data": {
    "message": {
      "uid": 345,
      "subject": "Hello",
      "from": {
        "address": "alice@example.com",
        "name": "Alice"
      },
      "to": [
        {
          "address": "archive@spktfpt.online",
          "name": ""
        }
      ],
      "date": "2026-04-13T10:00:00.000Z",
      "text": "plain text body",
      "html": "<p>html body</p>",
      "attachments": [
        {
          "index": 0,
          "filename": "invoice.pdf",
          "contentType": "application/pdf",
          "size": 12345
        }
      ],
      "envelope": {
        "subject": "Hello",
        "messageId": "<abc@example.com>"
      }
    }
  }
}
```

### `POST /api/mail/attachment`

Request (theo index):

```json
{
  "folder": "INBOX",
  "uid": 345,
  "attachmentIndex": 0
}
```

Response:

- Khong tra JSON.
- Tra binary stream, headers:
  - `Content-Type: application/pdf` (vi du)
  - `Content-Disposition: attachment; filename="invoice.pdf"`

### `POST /api/auth/tokens/list`

Request:

```json
{
  "email": "archive@spktfpt.online",
  "password": "ARCHIVE_PASSWORD"
}
```

Response:

```json
{
  "error_code": 0,
  "message": "OK",
  "data": {
    "tokens": [
      {
        "tokenId": "uuid",
        "createdAt": "2026-04-13T08:00:00.000Z",
        "refreshExpiresAt": "2026-07-12T08:00:00.000Z",
        "label": "admin-web",
        "revoked": false
      }
    ]
  }
}
```

### `POST /api/auth/revoke-by-id`

Request:

```json
{
  "tokenId": "uuid"
}
```

Response:

```json
{
  "error_code": 0,
  "message": "Token revoked by id",
  "data": {
    "revoked": true
  }
}
```
