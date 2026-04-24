# Tài liệu Frontend — PhishGuard

Tài liệu mô tả toàn bộ phần giao diện người dùng (client-side) của hệ thống phát hiện email lừa đảo PhishGuard. Frontend là Single Page Application (SPA) viết bằng vanilla JavaScript thuần, không sử dụng framework.

---

## 1. Tổng quan

| Thuộc tính | Giá trị |
|------------|--------|
| Kiến trúc | Single Page Application (SPA) |
| Ngôn ngữ | HTML5, CSS3, JavaScript ES6+ |
| Framework | Không (vanilla JS) |
| Build tool | Không (file tĩnh, phục vụ trực tiếp) |
| Giao tiếp backend | REST API qua `fetch` với cookie session |
| API base URL | `http://localhost:5000/api/v1` |
| Routing | Client-side hash routing (`#stats`, `#emails`, …) |

Toàn bộ UI được quản lý bởi một lớp `App` duy nhất trong [app.js](../frontend/js/app.js), một lớp phụ `ApiClient` trong [api.js](../frontend/js/api.js) đảm nhận gọi HTTP, và `AuthManager` trong [auth.js](../frontend/js/auth.js) quản lý trạng thái đăng nhập.

---

## 2. Cấu trúc thư mục

```
frontend/
├── index.html          # Shell HTML duy nhất của SPA
├── css/
│   └── style.css       # Design system (1383 dòng, pure CSS)
└── js/
    ├── api.js          # ApiClient — wrapper gọi REST API
    ├── auth.js         # AuthManager — quản lý phiên đăng nhập
    └── app.js          # App — logic chính, render UI (~3600 dòng)
```

Ngoài ra dự án còn thư mục [app/views/](../app/views/) và [app/static/](../app/static/) chứa các template Flask/Jinja kế thừa (legacy). SPA hiện tại không sử dụng các template này; chúng được giữ cho mục đích tham khảo và không ảnh hưởng luồng chính.

---

## 3. File `index.html`

File HTML duy nhất đóng vai trò "shell" cho SPA. Khi tải trang, nội dung động được JavaScript chèn vào các vùng `#login-overlay` hoặc `#app-content`.

**Các khối chính:**

- `<div id="login-overlay">` — Màn hình đăng nhập (email + password + label), hiển thị khi chưa đăng nhập.
- `<div id="app-shell">` — Khung ứng dụng gồm:
  - `<aside id="sidebar">` — Thanh điều hướng bên trái, hiển thị logo, menu, thông tin người dùng và nút đăng xuất.
  - `<header class="topbar">` — Thanh trên cùng: trạng thái tải dữ liệu, thời điểm đồng bộ cuối, nút bật/tắt sidebar trên mobile.
  - `<main id="app-content">` — Vùng render nội dung từng trang.

**Điểm vào sự kiện** (gắn trực tiếp vào HTML):

```html
<form onsubmit="app.handleLogin(event)">
<button onclick="app.toggleSidebar()">
```

Đối tượng `app` là một instance toàn cục của lớp `App` được khởi tạo ở cuối `app.js`.

---

## 4. File `css/style.css`

Design system Pure CSS gồm 1383 dòng, không phụ thuộc framework ngoài (không Tailwind, không Bootstrap).

### 4.1 Biến CSS chính

| Biến | Giá trị | Mô tả |
|------|---------|-------|
| `--primary` | `#6366f1` | Màu thương hiệu (indigo) |
| `--danger` | đỏ | Trạng thái phishing / nguy hiểm |
| `--warning` | vàng | Trạng thái suspicious |
| `--success` | xanh lá | Trạng thái legitimate |
| `--info` | xanh dương | Trạng thái trung tính |
| `--sidebar-bg` | `#1a1f2e` | Nền sidebar (dark theme) |

### 4.2 Các nhóm component

- **Layout:** Sidebar cố định + main content; responsive qua breakpoint 900px.
- **Cards, badges, buttons, alerts:** Thành phần UI chung cho toàn bộ trang.
- **Bảng dữ liệu:** Dùng cho danh sách email, lịch sử, VT results.
- **Biểu đồ:** Bar chart CSS-only (thanh chiều rộng theo tỉ lệ) cho top senders/domains, histogram phân bố xác suất, trend 14/30 ngày.
- **Animation:** Spinner loading, slide-down cho flash message, transition progress bar.
- **Responsive:** Grid 2 cột trên desktop, tự động thu về 1 cột trên mobile; sidebar chuyển sang overlay.

---

## 5. File `js/api.js` — Lớp `ApiClient`

Wrapper quản lý toàn bộ yêu cầu HTTP đến backend. Mọi request đều gửi với `credentials: "include"` để trình duyệt đính kèm cookie session.

### 5.1 Khởi tạo

```javascript
class ApiClient {
    constructor() {
        this.baseUrl = "http://localhost:5000/api/v1";
    }
    async request(path, options) { /* fetch + xử lý lỗi */ }
}
```

Nếu response trả về HTTP 401/403, client tự động gọi `checkAuthStatus()` và kích hoạt màn hình đăng nhập. Lỗi được bọc trong lớp `ApiError` với các loại: `AUTH_ERROR`, `NETWORK_ERROR`, `API_ERROR`.

### 5.2 Các nhóm phương thức

**Xác thực**
```javascript
checkAuthStatus()                   // GET  /auth/status
connectMail(email, password, label) // POST /auth/connect
disconnectGmail()                   // POST /auth/disconnect
```

**Email**
```javascript
fetchEmails(maxResults)             // POST /emails/fetch  — kéo email mới từ server mail
getEmails(limit, offset)            // GET  /emails/list
getEmail(emailId)                   // GET  /emails/{id}
getEmailPredictions(emailId)        // GET  /predictions/{email_id}/details
getEmailVTResults(emailId, ...)     // GET  /emails/{id}/vt-links
```

**Phân tích & dự đoán**
```javascript
analyzeEmail(emailText)                              // POST /predictions/analyze
analyzeStoredEmail(emailId)                          // POST /predictions/analyze-email/{id}
analyzeStoredEmailTranslated(emailId, translatedText)// POST /predictions/analyze-translated/{id}
analyzeBulkEmails(emailIds)                          // Gọi lần lượt cho từng email (có theo dõi tiến độ)
```

**Thống kê**
```javascript
getStatsOverview()          // GET /stats/overview
getStatsClassification()    // GET /stats/classification
getStatsTopSenders()        // GET /stats/top-senders
getStatsTopDomains()        // GET /stats/top-domains
getStatsTrend(days)         // GET /stats/trend
getStatsFeatures()          // GET /stats/features
getStatsSegments()          // GET /stats/segments
getStatsLinks(topN)         // GET /stats/links
getStatsTimeline(days)      // GET /stats/timeline
getStatsProbabilityDist()   // GET /stats/probability-dist
```

**Lịch sử đồng bộ**
```javascript
getFetchStatus()      // Tóm tắt trạng thái fetch
getFetchHistory()     // Danh sách log fetch
getAnalysisStatus()   // Trạng thái analyze
getAnalysisHistory()  // Log analyze
getVTStatus()         // Trạng thái VirusTotal (quota còn lại, hạn mức)
getVTHistory()        // Log quét VT
runVTScanNow()        // Kích hoạt quét thủ công
```

**Dịch thuật (Gemini)**
```javascript
translateTextToEnglish(text)                 // POST /translate/text
translateEmailBodyToEnglish(emailId)         // GET  /translate/{email_id}
getTranslationStatus()                       // GET  /translate/status
getTranslationHistory()                      // GET  /translate/history
```

---

## 6. File `js/auth.js` — Lớp `AuthManager`

Singleton quản lý trạng thái đăng nhập, được expose thông qua `window.authManager`.

```javascript
class AuthManager {
    isAuthenticated = false;
    user = null;                  // { id, email }
    onAuthStateChange = null;     // callback khi trạng thái thay đổi

    async checkStatus()           // Gọi /auth/status khi khởi động
    async connect(email, password, label)
    async disconnect()
    getUser()
    getIsAuthenticated()
}
```

Khi `checkStatus()` hoặc `connect()` trả về thành công, `AuthManager` cập nhật trạng thái rồi gọi callback để `App` ẩn login overlay và hiển thị shell.

---

## 7. File `js/app.js` — Lớp `App`

Tập trung toàn bộ logic SPA. Khi `window.onload` chạy, nó instantiate `new App()` và gán vào biến toàn cục `app`.

### 7.1 State chính

```javascript
class App {
    currentPage = "stats";          // Trang đang hiển thị
    selectedEmails = new Set();     // Email đang được tick trong bulk analyze
    emailManagementData = [];       // Cache email cho trang Management
    pollInterval = null;            // ID setInterval cho polling 30s
}
```

### 7.2 Hệ thống routing

Sử dụng hash routing để không cần server-side routing:

```javascript
setupRouting()            // Lắng nghe window.addEventListener("hashchange")
navigate(page)            // Thay đổi window.location.hash
async loadPage(page)      // Dispatch → render<Page>()
```

Các giá trị hash được hỗ trợ: `#stats`, `#emails`, `#manage`, `#analyze`, `#history`, `#fetch-history`.

### 7.3 Các trang và phương thức render

**`renderStats()` — Dashboard tổng quan**

Gọi song song toàn bộ `getStats*` và render:
- 5 stat card: Total, Phishing, Suspicious, Legitimate, VT links.
- Classification bar: tỉ lệ phishing vs benign.
- Top senders, top domains (bar chart chiều ngang).
- Xu hướng 14 ngày, timeline nhận email 30 ngày.
- Phân tích feature: số link trung bình, tỉ lệ có đính kèm, tỉ lệ có keyword khẩn cấp.
- VT link risk (malicious / suspicious / clean).
- Top 5 đoạn văn bản đáng ngờ.
- Histogram phân bố xác suất ML.

**`renderEmails()` — Danh sách email**

Bảng gồm cột: Subject, Sender, Date, Prediction badge, action "View". Click vào "View" gọi `viewEmail(emailId)` để hiển thị chi tiết.

**`renderAnalyze()` — Phân tích thủ công**

Giao diện 2 panel:
- Trái: dán nguyên văn email → nhấn "Analyze original".
- Phải: hiển thị bản dịch tiếng Anh sau khi "Translate" → nhấn "Analyze translation".

Sử dụng `translateTextToEnglish()` và `analyzeEmail()`.

**`renderHistory()` — Lịch sử dự đoán**

Bảng liệt kê toàn bộ prediction kèm: tiêu đề, người gửi, prediction badge, nguồn input (`original` hoặc `translated_body`), độ tin cậy, ngày.

**`renderEmailManagement()` — Quản lý và phân tích hàng loạt**

- Checkbox chọn nhiều email, action bar "Analyze Selected".
- Khi có email được chọn, hiển thị analytics tức thời: Total, % Phishing, độ tin cậy trung bình, dải min–max.
- Progress bar khi gọi `analyzeBulkEmails()` tuần tự.

**`renderFetchHistory()` — Nhật ký đồng bộ**

- Status card: tổng email, lần fetch cuối, số email chưa phân tích, quota VT còn lại.
- Bảng fetch log (Auto / Manual).
- Bảng analysis log.
- Bảng VT scan log + bảng kết quả chi tiết URL (status, số detection).
- Bảng translation log + thống kê (chunk sử dụng, tỉ lệ thành công).

### 7.4 Các hàm xử lý chính

```javascript
// Đăng nhập
async handleLogin(event)          // onsubmit của form login
showLoginOverlay(), hideLoginOverlay()

// Sidebar
updateSidebar()                   // Render menu + thông tin user
toggleSidebar()

// Polling (mỗi 30 giây)
startPolling(), stopPolling()
async pollForNewEmails()          // Kiểm tra fetch status, cập nhật badge

// Thao tác email
async viewEmail(emailId)
async fetchEmails()
async translateAnalyzeTextToEnglish()

// Phân tích hàng loạt
async analyzeAllEmails()
async analyzeSelectedEmails()

// UI helper
showLoading(), hideLoading()
showSuccess(msg), showError(msg)
renderPredictionBadge(pred)       // Badge theo classification
escapeHtml(str)                   // Chống XSS khi inject HTML
```

---

## 8. Giao tiếp với backend

### 8.1 Cơ chế xác thực

- Dùng session cookie (không lưu token trong `localStorage`).
- Mọi `fetch` gửi kèm `credentials: "include"` để trình duyệt tự đính kèm cookie.
- Khi backend trả 401, `ApiClient` gọi `checkAuthStatus()` rồi `AuthManager` hiển thị lại login overlay.

### 8.2 Ví dụ request/response

**Đăng nhập**
```http
POST /api/v1/auth/connect
Content-Type: application/json

{ "email": "user@example.com", "password": "…", "label": "INBOX" }
```

**Lấy danh sách email**
```http
GET /api/v1/emails/list?limit=50&offset=0
Cookie: session=…
```

**Phân tích thủ công**
```http
POST /api/v1/predictions/analyze
Content-Type: application/json

{ "email_text": "…" }
```

### 8.3 Luồng người dùng tiêu biểu

```
Mở trang → checkStatus()
  │
  ├── Chưa đăng nhập → showLoginOverlay() → handleLogin() → connect()
  │
  └── Đã đăng nhập → hideLoginOverlay() → loadPage("stats")
        │
        ├── Dashboard: renderStats() + polling 30 s
        ├── Emails:    renderEmails() → viewEmail()
        ├── Analyze:   renderAnalyze() → translate/analyze
        ├── Manage:    renderEmailManagement() → bulk analyze
        ├── History:   renderHistory()
        └── Sync log:  renderFetchHistory()
```

---

## 9. Bảo mật phía client

- **Chống XSS:** Mọi giá trị do backend trả về (subject, sender, body, URL…) đều được đưa qua `escapeHtml()` trước khi inject vào HTML thông qua template literal.
- **Không lưu credential:** Password chỉ tồn tại trong bộ nhớ form trong quá trình submit; không ghi vào `localStorage`/`sessionStorage`.
- **Session-only:** Cookie session do backend kiểm soát (HttpOnly, SameSite=Lax), JavaScript không đọc được.

---

## 10. Các module UI và endpoint tương ứng

| Module           | Mô tả                                         | Endpoint tiêu biểu                                           |
|------------------|-----------------------------------------------|--------------------------------------------------------------|
| Login            | Form email + password                         | `/auth/connect`, `/auth/status`, `/auth/disconnect`          |
| Dashboard        | Stat card, xu hướng, biểu đồ                  | `/stats/*` (10 endpoint)                                     |
| Emails List      | Bảng danh sách email                          | `/emails/list`                                               |
| Email Detail     | Chi tiết + prediction + VT links              | `/emails/{id}`, `/predictions/{email_id}/details`            |
| Analyze          | Dán text, dịch, phân tích                     | `/predictions/analyze`, `/translate/text`                    |
| Management       | Bulk analyze                                  | `/emails/list`, `/predictions/analyze-email/{id}`            |
| History          | Lịch sử dự đoán                               | `/history/predictions`                                       |
| Sync Log         | Fetch, analyze, VT, translation log           | `/emails/fetch-history`, `/emails/analysis-history`, `/emails/vt-history`, `/translate/history` |

---

## 11. Chạy và phát triển

Vì frontend là file tĩnh, có thể phục vụ bằng bất kỳ web server nào:

```bash
# Ví dụ: dùng Python
cd frontend
python -m http.server 5001
# Sau đó mở http://localhost:5001
```

Yêu cầu backend phải đang chạy tại `http://localhost:5000` và origin `http://localhost:5001` phải nằm trong `CORS_ORIGINS` của backend.

---

## 12. Chi tiết triển khai

Phần này tham chiếu trực tiếp đến mã nguồn trong [frontend/](../frontend/) và đi sâu vào các pattern quan trọng. Các sơ đồ tuần tự của từng luồng xem [SEQUENCE_DIAGRAMS.md](./SEQUENCE_DIAGRAMS.md).

### 12.1 Khởi tạo và vòng đời trang

Khi trình duyệt tải `index.html`, script được load theo thứ tự: `api.js` → `auth.js` → `app.js`. Ở cuối `app.js`:

```javascript
const api = new ApiClient();
const authManager = new AuthManager(api);
window.app = new App(api, authManager);

window.addEventListener("DOMContentLoaded", () => {
    window.app.init();
});
```

`App.init()` thực hiện 4 bước:

1. Gắn hash router (`window.addEventListener("hashchange", ...)`).
2. Gọi `authManager.checkStatus()` — một lần duy nhất khi khởi động.
3. Nếu đã đăng nhập: `hideLoginOverlay()` → `loadPage(currentPage)` → `startPolling()`.
4. Nếu chưa: `showLoginOverlay()`, form login sẽ tự kích hoạt flow đăng nhập.

### 12.2 `ApiClient.request()` — cốt lõi của mọi fetch

Tất cả phương thức trong `ApiClient` đều quy về một hàm duy nhất:

```javascript
async request(path, { method = "GET", body = null, query = null } = {}) {
    const url = new URL(this.baseUrl + path);
    if (query) {
        Object.entries(query).forEach(([k, v]) =>
            v !== undefined && v !== null && url.searchParams.set(k, v)
        );
    }

    const options = {
        method,
        credentials: "include",
        headers: { "Content-Type": "application/json" },
    };
    if (body) options.body = JSON.stringify(body);

    let response;
    try {
        response = await fetch(url, options);
    } catch (err) {
        throw new ApiError("Network error", "NETWORK_ERROR", err);
    }

    if (response.status === 401 || response.status === 403) {
        // Yêu cầu login lại
        authManager.isAuthenticated = false;
        authManager.onAuthStateChange?.(false);
        throw new ApiError("Auth required", "AUTH_ERROR");
    }

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new ApiError(payload.detail || "API error", "API_ERROR", payload);
    }
    return payload;
}
```

Lưu ý:
- `credentials: "include"` gửi cookie session trên mọi domain backend đã được CORS allow.
- Trên lỗi 401/403, lớp trên sẽ catch `ApiError` với `type === "AUTH_ERROR"` và trình diễn login overlay.
- Lỗi JSON parse được nuốt để tránh throw khi backend trả body rỗng.

### 12.3 Hash router

SPA chia theo hash (`#stats`, `#emails`, …). `setupRouting()` đăng ký listener rồi gọi `loadPage` cho hash hiện tại:

```javascript
setupRouting() {
    window.addEventListener("hashchange", () => this.loadPage(this.getCurrentHash()));
    const initial = this.getCurrentHash() || "stats";
    this.loadPage(initial);
}

getCurrentHash() {
    return window.location.hash.replace(/^#/, "") || "stats";
}

async loadPage(page) {
    this.currentPage = page;
    this.updateSidebar();
    this.showLoading();
    try {
        switch (page) {
            case "stats":          await this.renderStats(); break;
            case "emails":         await this.renderEmails(); break;
            case "analyze":        await this.renderAnalyze(); break;
            case "manage":         await this.renderEmailManagement(); break;
            case "history":        await this.renderHistory(); break;
            case "fetch-history":  await this.renderFetchHistory(); break;
            default: this.renderStats();
        }
    } catch (err) {
        this.showError(err.message);
    } finally {
        this.hideLoading();
    }
}
```

### 12.4 Polling email mới

Sau khi đăng nhập, SPA bật interval 30 giây:

```javascript
startPolling() {
    if (this.pollInterval) return;
    this.pollInterval = setInterval(() => this.pollForNewEmails(), 30_000);
}

async pollForNewEmails() {
    try {
        const status = await api.getFetchStatus();
        if (status.unanalyzed > this._lastUnanalyzed) {
            this.showToast(`${status.unanalyzed - this._lastUnanalyzed} email mới`);
            if (this.currentPage === "stats") this.renderStats();
            if (this.currentPage === "emails") this.renderEmails();
        }
        this._lastUnanalyzed = status.unanalyzed;
    } catch (_) {
        // Không ảnh hưởng UI chính, chỉ log silent
    }
}

stopPolling() {
    clearInterval(this.pollInterval);
    this.pollInterval = null;
}
```

### 12.5 Chống XSS

Backend trả nội dung email thô; SPA dùng `escapeHtml()` trước mọi `innerHTML`:

```javascript
escapeHtml(str) {
    if (str == null) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

renderEmailRow(email) {
    return `
        <tr>
            <td>${this.escapeHtml(email.subject)}</td>
            <td>${this.escapeHtml(email.sender)}</td>
            <td>${this.formatDate(email.received_at)}</td>
            <td>${this.renderPredictionBadge(email.prediction)}</td>
        </tr>`;
}
```

**Hộp thoại body email** là trường hợp đặc biệt — backend trả HTML. SPA chèn vào một `<iframe srcdoc>` cách ly với DOM chính để vô hiệu script:

```javascript
`<iframe sandbox="" srcdoc="${this.escapeHtml(body)}"></iframe>`
```

### 12.6 Prediction badge

```javascript
renderPredictionBadge(pred) {
    if (!pred) return `<span class="badge badge-muted">Chưa phân tích</span>`;
    const map = {
        PHISHING:   ["danger",  "Phishing"],
        SUSPICIOUS: ["warning", "Nghi ngờ"],
        LEGITIMATE: ["success", "An toàn"],
    };
    const [cls, label] = map[pred.classification] || ["muted", pred.classification];
    const score = (pred.ensemble_score * 100).toFixed(1);
    return `<span class="badge badge-${cls}">${label} · ${score}%</span>`;
}
```

### 12.7 Bar chart CSS-only

Thay vì thư viện biểu đồ, các bar chart ngang tận dụng `width: calc(... * 100%)`:

```javascript
renderBarList(items, maxKey = "count") {
    const max = Math.max(...items.map(it => it[maxKey])) || 1;
    return items.map(it => {
        const pct = (it[maxKey] / max) * 100;
        return `
            <div class="bar-row">
                <span class="bar-label">${this.escapeHtml(it.label)}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width:${pct.toFixed(1)}%"></div>
                </div>
                <span class="bar-value">${it[maxKey]}</span>
            </div>`;
    }).join("");
}
```

### 12.8 Bulk analyze — tracking tiến độ

```javascript
async analyzeSelectedEmails() {
    const ids = [...this.selectedEmails];
    this.showProgress(0, ids.length);
    const results = [];
    for (let i = 0; i < ids.length; i++) {
        try {
            const r = await api.analyzeStoredEmail(ids[i]);
            results.push(r);
        } catch (err) {
            results.push({ error: err.message, email_id: ids[i] });
        }
        this.showProgress(i + 1, ids.length);
    }
    this.renderBulkSummary(results);
}
```

Frontend gọi **tuần tự** thay vì `Promise.all` để:
- Hiển thị progress bar chính xác.
- Tránh quá tải model ML (load lazy 1 lần nhưng predict_proba vẫn tốn CPU).
- Giới hạn rate VT / Gemini khi backend tự trigger thêm các hành động phụ.

### 12.9 Form login

```javascript
async handleLogin(event) {
    event.preventDefault();
    const form = event.target;
    const email = form.email.value.trim();
    const password = form.password.value;
    const label = form.label.value || "INBOX";

    this.showLoading("Đang đăng nhập...");
    try {
        await authManager.connect(email, password, label);
        this.hideLoginOverlay();
        this.startPolling();
        await this.loadPage("stats");
    } catch (err) {
        this.showError(err.message || "Sai tài khoản");
    } finally {
        this.hideLoading();
        form.password.value = "";    // Không giữ password trong DOM
    }
}
```

### 12.10 Ví dụ JSON request/response tiêu biểu

**`POST /api/v1/predictions/analyze` — request**
```json
{
  "email_text": "Dear customer, your account will be suspended...",
  "subject": "Urgent: Verify your identity",
  "has_attachment": 0,
  "links_count": 3,
  "sender_domain": "paypa1.com",
  "urgent_keywords": 1
}
```

**Response**
```json
{
  "prediction": 1,
  "classification": "PHISHING",
  "probability": 0.912,
  "ensemble_score": 0.874,
  "threshold": 0.6,
  "suspicious_margin": 0.2,
  "is_phishing": true,
  "features": {
    "links_count": 3,
    "has_attachment": 0,
    "urgent_keywords": 1,
    "sender_domain": "paypa1.com",
    "sender_risk": "SUSPICIOUS"
  },
  "formula_details": {
    "model_component":   0.502,
    "urgent_component":  0.200,
    "links_component":   0.105,
    "domain_component":  0.067
  },
  "suspicious_segments": [
    {
      "text": "Your account will be suspended within 24 hours...",
      "score": 87.5,
      "severity": "HIGH",
      "reasons": ["urgent_keyword", "threat_language"]
    }
  ]
}
```

**`GET /api/v1/stats/overview` — response**
```json
{
  "total_emails": 342,
  "analyzed": 340,
  "unanalyzed": 2,
  "phishing_count": 23,
  "suspicious_count": 41,
  "legitimate_count": 276,
  "threat_rate": 0.188,
  "vt_link_stats": { "malicious": 5, "suspicious": 12, "clean": 188 }
}
```

### 12.11 Xử lý lỗi UI nhất quán

`showError()` hiển thị flash message đỏ trong topbar:

```javascript
showError(message) {
    const el = document.getElementById("flash");
    el.textContent = message;
    el.className = "flash flash-danger show";
    clearTimeout(this._flashTimer);
    this._flashTimer = setTimeout(() => el.classList.remove("show"), 4000);
}

showSuccess(message) { /* tương tự với .flash-success */ }
```

### 12.12 Tham chiếu sơ đồ tuần tự

| Luồng | Sequence diagram |
|-------|------------------|
| Đăng nhập | [1. Đăng nhập](./SEQUENCE_DIAGRAMS.md#1-đăng-nhập-mail-api-connect) |
| Kiểm tra phiên | [2. Kiểm tra phiên](./SEQUENCE_DIAGRAMS.md#2-kiểm-tra-phiên-khi-khởi-động-spa) |
| Fetch email | [4. Fetch email thủ công](./SEQUENCE_DIAGRAMS.md#4-fetch-email-thủ-công) |
| Phân tích paste text | [8. Phân tích email thủ công](./SEQUENCE_DIAGRAMS.md#8-phân-tích-email-thủ-công-paste-text) |
| Translate + analyze | [9. Dịch + phân tích bản dịch](./SEQUENCE_DIAGRAMS.md#9-dịch--phân-tích-bản-dịch) |
| Dashboard | [11. Dashboard stats](./SEQUENCE_DIAGRAMS.md#11-dashboard-stats) |
| Bulk analyze | [12. Bulk analyze](./SEQUENCE_DIAGRAMS.md#12-bulk-analyze-frontend) |
| Chi tiết email | [13. Xem chi tiết email](./SEQUENCE_DIAGRAMS.md#13-xem-chi-tiết-email) |
