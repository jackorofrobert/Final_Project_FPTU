# Frontend Documentation

## Overview

The frontend is a single-page application (SPA) built with vanilla JavaScript, HTML5, and CSS3. It communicates with the FastAPI backend through REST API endpoints. The application provides a user-friendly interface for Gmail authentication, email fetching, phishing detection analysis, and viewing prediction history.

**Technology Stack**:
- Vanilla JavaScript (ES6+)
- HTML5
- CSS3
- No external frameworks or libraries

**File Structure**:
```
frontend/
├── index.html          # Main HTML file
├── css/
│   └── style.css       # Application styles
└── js/
    ├── api.js          # API client module
    ├── auth.js         # Authentication manager
    └── app.js          # Main application logic
```

## Architecture

### Module Structure

The frontend is organized into three main JavaScript modules:

1. **`api.js`** - API Client
   - Handles all HTTP requests to the backend
   - Provides error handling and response parsing
   - Manages authentication state in requests

2. **`auth.js`** - Authentication Manager
   - Manages user authentication state
   - Handles OAuth2 flow initiation
   - Provides authentication status checking

3. **`app.js`** - Main Application
   - Manages routing and page navigation
   - Renders UI components
   - Handles user interactions
   - Coordinates between API and Auth modules

### Application Flow

```
User Action → App.js → API.js → Backend API
                ↓
            Auth.js (for auth checks)
                ↓
            UI Update
```

## Pages and Components

### 1. Home Page

**Route**: `#home` (default)

**Description**: Landing page with feature overview and quick actions.

**Features**:
- Hero section with application title
- Feature cards showing main capabilities:
  - Connect Gmail
  - Fetch Emails
  - Analyze Email
  - View History
- Authentication status display
- Quick action buttons

**Code Location**: `app.js` → `renderHome()`

### 2. Email List Page

**Route**: `#emails`

**Description**: Displays a list of emails fetched from Gmail.

**Features**:
- Table view of emails with columns:
  - Subject
  - Sender
  - Date
  - Prediction status (Phishing/Benign/Not Analyzed)
  - Actions (View button)
- Pagination support
- "Fetch Emails" button if no emails found
- Authentication required

**Code Location**: `app.js` → `renderEmails()`

### 3. Email Management Page

**Route**: `#manage`

**Description**: Advanced email management with bulk operations and analytics.

**Features**:
- Email list with checkboxes for selection
- Select all / Clear selection
- Bulk action bar (shown when emails are selected):
  - Analyze Selected button
  - Selected count display
- Global actions:
  - Analyze All Emails button
- Analytics Dashboard (shown when emails are selected):
  - Total selected count
  - Phishing count and percentage
  - Benign count and percentage
  - Not analyzed count
  - Average confidence score
  - Confidence range
  - Visual breakdown bar (Phishing vs Benign)
- Individual email actions (View button)

**Code Location**: `app.js` → `renderEmailManagement()`

### 4. Analyze Page

**Route**: `#analyze`

**Description**: Manual email analysis interface.

**Features**:
- Text area for email content input
- Analyze button
- Results display area showing:
  - Prediction (Phishing/Benign)
  - Confidence score
  - Probability percentage
  - Visual indicators (badges)

**Code Location**: `app.js` → `renderAnalyze()`

### 5. History Page

**Route**: `#history`

**Description**: Displays prediction history for authenticated user.

**Features**:
- Table view of predictions with columns:
  - Email Subject
  - Sender
  - Prediction (Phishing/Benign)
  - Confidence percentage
  - Date
  - Actions (View Email button)
- Pagination support
- Authentication required

**Code Location**: `app.js` → `renderHistory()`

### 6. Email Detail View

**Route**: Modal/Overlay (not a separate route)

**Description**: Detailed view of a single email.

**Features**:
- Email metadata (subject, sender, recipient, date)
- Full email body content
- Prediction results (if analyzed):
  - Prediction label
  - Confidence score
  - Model version
  - Analysis timestamp
- Action buttons:
  - Analyze Email (if not analyzed)
  - View Predictions (if analyzed)
- Close button

**Code Location**: `app.js` → `viewEmail()`

## JavaScript Modules

### API Client (`api.js`)

**Class**: `ApiClient`

**Purpose**: Centralized API communication layer.

**Key Methods**:
- `request(endpoint, options)` - Generic HTTP request handler
- `get(endpoint, options)` - GET request
- `post(endpoint, data, options)` - POST request
- `checkAuthStatus()` - Check authentication status
- `connectGmail()` - Initiate OAuth2 flow
- `disconnectGmail()` - Disconnect Gmail account
- `fetchEmails(maxResults)` - Fetch emails from Gmail
- `getEmails(limit, offset)` - Get stored emails list
- `getEmail(emailId)` - Get email details
- `getEmailPredictions(emailId)` - Get email prediction history
- `analyzeEmail(emailText)` - Analyze email text
- `analyzeStoredEmail(emailId)` - Analyze stored email
- `analyzeBulkEmails(emailIds)` - Bulk analyze emails
- `getPredictionHistory(limit, offset)` - Get prediction history

**Error Handling**:
- Custom `ApiError` class with error types:
  - `AUTH_ERROR` - Authentication failures
  - `NETWORK_ERROR` - Network connectivity issues
  - `API_ERROR` - Server errors
  - `UNKNOWN_ERROR` - Unexpected errors
- Automatic authentication status refresh on 401/403
- User-friendly error messages

**Configuration**:
- Base URL: `http://localhost:5001/api/v1`
- Credentials: `include` (for session cookies)
- Content-Type: `application/json`

### Authentication Manager (`auth.js`)

**Class**: `AuthManager`

**Purpose**: Manages user authentication state and OAuth2 flow.

**Properties**:
- `isAuthenticated` (boolean) - Current authentication status
- `user` (object) - User information (id, email)
- `onAuthStateChange` (function) - Callback for auth state changes

**Key Methods**:
- `checkStatus()` - Check current authentication status
- `connectGmail()` - Initiate OAuth2 connection flow
- `disconnect()` - Disconnect Gmail account
- `getUser()` - Get current user information
- `getIsAuthenticated()` - Get authentication status
- `clearAuthState()` - Clear authentication state
- `setOnAuthStateChange(callback)` - Set callback for auth state changes

**OAuth2 Flow**:
1. User clicks "Connect Gmail"
2. `connectGmail()` called → API request to `/api/v1/auth/connect`
3. Server returns authorization URL
4. User redirected to Google OAuth2 consent screen
5. User grants permissions
6. Google redirects to `/api/v1/auth/callback`
7. Server processes callback and sets session
8. Frontend detects `#auth-success` hash
9. Authentication status updated

### Main Application (`app.js`)

**Class**: `App`

**Purpose**: Main application controller managing routing, UI rendering, and user interactions.

**Properties**:
- `currentPage` (string) - Current active page
- `selectedEmails` (Set) - Selected email IDs for bulk operations
- `emailManagementData` (array) - Cached email list data

**Key Methods**:

**Initialization**:
- `init()` - Initialize application
- `setupRouting()` - Set up client-side routing
- `handleAuthCallback()` - Handle OAuth callback

**Navigation**:
- `navigate(page, pushState)` - Navigate to page
- `loadPage(page)` - Load and render page
- `updateNavigation()` - Update navigation UI

**Page Rendering**:
- `renderHome()` - Render home page
- `renderEmails()` - Render email list page
- `renderEmailManagement()` - Render email management page
- `renderAnalyze()` - Render analyze page
- `renderHistory()` - Render history page
- `viewEmail(emailId)` - Show email detail view

**Email Operations**:
- `fetchEmails()` - Fetch emails from Gmail
- `analyzeEmail(emailId)` - Analyze a single email
- `analyzeSelectedEmails()` - Analyze selected emails (bulk)
- `analyzeAllEmails()` - Analyze all emails

**Email Management**:
- `toggleEmailSelection(emailId, isSelected)` - Toggle email selection
- `toggleSelectAll(selectAll)` - Select/deselect all emails
- `clearSelection()` - Clear all selections
- `updateBulkActionBar()` - Update bulk action bar visibility
- `updateAnalyticsDashboard()` - Update analytics dashboard
- `renderEmailList(emails)` - Render email list table

**UI Utilities**:
- `showLoading()` - Show loading indicator
- `hideLoading()` - Hide loading indicator
- `showSuccess(message)` - Show success message
- `showError(message)` - Show error message
- `getUserFriendlyErrorMessage(error, defaultMessage)` - Format error messages

## User Flows

### 1. Authentication Flow

```
1. User clicks "Connect Gmail" button
2. App calls authManager.connectGmail()
3. API returns authorization URL
4. User redirected to Google OAuth2 consent screen
5. User grants permissions
6. Google redirects to /api/v1/auth/callback
7. Server processes callback, sets session
8. Frontend detects #auth-success hash
9. Success message shown
10. Authentication status updated
11. UI updated to show authenticated state
```

### 2. Email Fetching Flow

```
1. User clicks "Fetch Emails" button
2. App calls api.fetchEmails(maxResults)
3. Loading indicator shown
4. API request to POST /api/v1/emails/fetch
5. Server fetches emails from Gmail API
6. Emails stored in database
7. Response returned with email list
8. UI updated with fetched emails
9. Success message shown
```

### 3. Email Analysis Flow

**Manual Analysis**:
```
1. User navigates to Analyze page
2. User enters email text in textarea
3. User clicks "Analyze" button
4. App calls api.analyzeEmail(emailText)
5. API request to POST /api/v1/predictions/analyze
6. Server processes email through ML model
7. Prediction result returned
8. Results displayed on page
```

**Stored Email Analysis**:
```
1. User views email list
2. User clicks "Analyze" on an email
3. App calls api.analyzeStoredEmail(emailId)
4. API request to POST /api/v1/predictions/analyze-email/{emailId}
5. Server processes email through ML model
6. Prediction saved to database
7. UI updated with prediction result
8. Success message shown
```

**Bulk Analysis**:
```
1. User navigates to Email Management page
2. User selects multiple emails (checkboxes)
3. User clicks "Analyze Selected" button
4. App calls api.analyzeBulkEmails(emailIds)
5. For each email:
   - API request to analyze endpoint
   - Results collected
6. Success/failure summary shown
7. UI updated with all prediction results
```

### 4. History Viewing Flow

```
1. User navigates to History page
2. App calls api.getPredictionHistory()
3. API request to GET /api/v1/history/predictions
4. Server returns prediction history
5. History table rendered
6. User can click "View Email" to see details
```

## Routing

The application uses client-side routing with URL hash fragments:

- `#home` - Home page (default)
- `#emails` - Email list page
- `#manage` - Email management page
- `#analyze` - Analyze page
- `#history` - History page
- `#auth-success` - OAuth success callback
- `#auth-error=<message>` - OAuth error callback

**Routing Implementation**:
- Hash-based routing (no page reloads)
- Browser history support (back/forward buttons)
- Navigation via `data-page` attributes on links
- Programmatic navigation via `app.navigate(page)`

## Styling

### CSS Architecture

The application uses a custom CSS file (`style.css`) with:

**Design System**:
- Color scheme: Dark blue navbar (#2c3e50), light gray background (#f5f5f5)
- Typography: System font stack
- Spacing: Consistent padding and margins
- Responsive: Container-based layout with max-width

**Component Styles**:
- Navigation bar
- Buttons (primary, secondary, small variants)
- Forms and inputs
- Tables (email list, history)
- Cards (feature cards, analytics cards)
- Badges (status indicators)
- Flash messages (success, error, warning, info)
- Modals/Overlays

**Utility Classes**:
- `.container` - Content container
- `.btn` - Button base class
- `.badge` - Status badge
- `.text-muted` - Muted text
- `.selected` - Selected row styling

## Error Handling

### Error Types

1. **Authentication Errors**:
   - Session expired
   - Not authenticated
   - OAuth flow failures
   - Automatic redirect to home page

2. **Network Errors**:
   - Connection failures
   - Timeout errors
   - User-friendly messages displayed

3. **API Errors**:
   - Server errors (500)
   - Validation errors (400, 422)
   - Not found errors (404)
   - Error messages displayed to user

4. **User Errors**:
   - Missing required fields
   - Invalid input
   - Inline validation messages

### Error Display

- Flash messages at top of page
- Color-coded (red for errors, green for success)
- Auto-dismiss after timeout (optional)
- Persistent until user dismisses

## State Management

### Application State

- **Authentication State**: Managed by `AuthManager`
  - Stored in memory
  - Persisted via session cookies (server-side)
  - Checked on page load

- **Page State**: Managed by `App`
  - Current page stored in `currentPage`
  - URL hash reflects current page

- **Selection State**: Managed by `App`
  - `selectedEmails` Set for bulk operations
  - Persists during page session
  - Cleared on page navigation

- **Data State**: Managed by `App`
  - `emailManagementData` cached for analytics
  - Refreshed on page load

## Integration with Backend

### API Communication

All frontend-backend communication happens through REST API:

1. **Authentication**: Session-based via cookies
   - Cookies set by server after OAuth callback
   - Included automatically in requests (`credentials: 'include'`)

2. **Data Fetching**: GET requests
   - Email list: `GET /api/v1/emails/list`
   - Email details: `GET /api/v1/emails/{id}`
   - Prediction history: `GET /api/v1/history/predictions`

3. **Data Submission**: POST requests
   - OAuth initiation: `POST /api/v1/auth/connect`
   - Email fetching: `POST /api/v1/emails/fetch`
   - Email analysis: `POST /api/v1/predictions/analyze`

4. **Error Handling**: Consistent error response format
   - All errors return `{ success: false, message: "...", error: "..." }`
   - HTTP status codes indicate error type
   - Frontend displays user-friendly messages

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ JavaScript features
- Fetch API for HTTP requests
- CSS Grid and Flexbox for layout
- No polyfills required for modern browsers

## Performance Considerations

- Lazy loading of email details
- Efficient DOM updates (only changed elements)
- Caching of email list data for analytics
- Minimal external dependencies (vanilla JS)
- Optimized API calls (bulk operations where possible)

## Security

- Session-based authentication (secure cookies)
- No sensitive data stored in localStorage
- OAuth2 flow handled securely
- CORS configured on backend
- Input validation on both frontend and backend

## Future Enhancements

Potential improvements:
- Real-time updates (WebSocket)
- Offline support (Service Workers)
- Progressive Web App (PWA) features
- Advanced filtering and search
- Export functionality
- Email preview pane
- Dark mode theme
