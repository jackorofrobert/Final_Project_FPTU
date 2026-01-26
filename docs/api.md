# API Documentation

## Overview

The Phishing Email Detection System provides a RESTful API built with FastAPI. The API enables users to authenticate via Gmail OAuth2, fetch emails from Gmail, analyze emails for phishing detection, and view prediction history.

**Base URL**: `http://localhost:5001/api/v1`

**API Version**: v1

**Documentation**: 
- Swagger UI: `http://localhost:5001/docs`
- ReDoc: `http://localhost:5001/redoc`
- OpenAPI Schema: `http://localhost:5001/openapi.json`

## Authentication

The API uses OAuth2 authentication with Google Gmail. Most endpoints require authentication via session cookies. The authentication flow is as follows:

1. Client calls `POST /api/v1/auth/connect` to initiate OAuth2 flow
2. Server returns an authorization URL
3. User is redirected to Google OAuth2 consent screen
4. User grants permissions
5. Google redirects to `/api/v1/auth/callback` with authorization code
6. Server exchanges code for tokens and stores them encrypted in database
7. Server sets session cookies and redirects to frontend

### Authentication Status

Check if the current session is authenticated:

**Endpoint**: `GET /api/v1/auth/status`

**Authentication**: Optional

**Response**:
```json
{
  "success": true,
  "data": {
    "authenticated": true,
    "user_id": 1,
    "user_email": "user@example.com"
  }
}
```

## Authentication Endpoints

### 1. Initiate OAuth2 Flow

**Endpoint**: `POST /api/v1/auth/connect`

**Authentication**: Not required

**Description**: Starts the OAuth2 authentication flow with Gmail. Returns an authorization URL that the user should visit to grant access.

**Request Body**: Empty object `{}`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
    "state": "random_state_string_12345"
  },
  "message": "OAuth2 flow initiated"
}
```

**Error Response** (500):
```json
{
  "success": false,
  "error": "OAuth2 configuration error",
  "message": "Failed to initiate OAuth2 flow"
}
```

### 2. OAuth2 Callback

**Endpoint**: `GET /api/v1/auth/callback`

**Authentication**: Not required

**Description**: Handles the OAuth2 callback from Google. This endpoint processes the authorization code and completes the authentication flow. Redirects to the frontend with success or error status.

**Query Parameters**:
- `code` (string, optional): Authorization code from Google
- `state` (string, optional): OAuth state parameter for CSRF protection
- `error` (string, optional): Error code if OAuth flow failed

**Response**: HTTP 302 Redirect to frontend with hash parameter:
- Success: `/#auth-success`
- Error: `/#auth-error=<error_message>`

### 3. Disconnect Gmail Account

**Endpoint**: `POST /api/v1/auth/disconnect`

**Authentication**: Required

**Description**: Disconnects the authenticated Gmail account by removing stored OAuth tokens and clearing the user session.

**Request Body**: Empty object `{}`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Gmail account disconnected"
}
```

**Error Response** (401):
```json
{
  "success": false,
  "message": "Authentication required"
}
```

## Email Endpoints

### 1. Fetch Emails from Gmail

**Endpoint**: `POST /api/v1/emails/fetch`

**Authentication**: Required

**Description**: Fetches emails from the authenticated user's Gmail account using the Gmail API. Emails are fetched and stored in the database for analysis.

**Request Body**:
```json
{
  "max_results": 50
}
```

**Parameters**:
- `max_results` (integer, optional): Maximum number of emails to fetch (default: 50, max: 500)

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
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
  },
  "message": "Successfully fetched and stored 3 emails"
}
```

**Error Responses**:
- 401: Authentication required
- 500: Error fetching emails

### 2. List Stored Emails

**Endpoint**: `GET /api/v1/emails/list`

**Authentication**: Required

**Description**: Retrieves a paginated list of emails stored in the database for the authenticated user. Each email includes its latest prediction if available.

**Query Parameters**:
- `limit` (integer, optional): Number of emails to return (default: 50, min: 1, max: 100)
- `offset` (integer, optional): Number of emails to skip for pagination (default: 0)

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
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
}
```

**Error Responses**:
- 401: Authentication required
- 500: Error retrieving email list

### 3. Get Email Details

**Endpoint**: `GET /api/v1/emails/{email_id}`

**Authentication**: Required

**Description**: Retrieves detailed information about a specific email, including its content and latest prediction result. Requires authentication and ownership of the email.

**Path Parameters**:
- `email_id` (integer): The ID of the email to retrieve

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "user_id": 1,
    "gmail_message_id": "abc123",
    "subject": "Important: Verify Your Account",
    "sender": "noreply@example.com",
    "recipient": "user@example.com",
    "body": "Please verify your account...",
    "received_at": "2024-01-15T10:30:00Z",
    "prediction": {
      "id": 1,
      "prediction": 1,
      "probability": 0.95,
      "is_phishing": true
    }
  }
}
```

**Error Responses**:
- 401: Authentication required
- 404: Email not found
- 500: Error retrieving email

### 4. Get Email Predictions

**Endpoint**: `GET /api/v1/emails/{email_id}/predictions`

**Authentication**: Required

**Description**: Retrieves all prediction history for a specific email. Returns a list of all predictions made for the email, including historical predictions if the email was analyzed multiple times.

**Path Parameters**:
- `email_id` (integer): The ID of the email to get predictions for

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "predictions": [
      {
        "id": 1,
        "email_id": 123,
        "prediction": 1,
        "probability": 0.95,
        "model_version": "1.0.0",
        "created_at": "2024-01-15T10:40:00Z"
      }
    ]
  }
}
```

**Error Responses**:
- 401: Authentication required or access denied
- 500: Error retrieving predictions

## Prediction Endpoints

### 1. Analyze Email Text

**Endpoint**: `POST /api/v1/predictions/analyze`

**Authentication**: Optional (if authenticated, prediction is saved to database)

**Description**: Analyzes email text for phishing detection using the ML model. This endpoint accepts raw email text and returns a prediction result.

**Request Body**:
```json
{
  "email_text": "Urgent: Verify your bank account immediately"
}
```

**Parameters**:
- `email_text` (string, required): The email content to analyze

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "prediction": 1,
    "probability": 0.95,
    "threshold": 0.5,
    "email_id": 123,
    "is_phishing": true
  },
  "message": "Email analyzed successfully"
}
```

**Response Fields**:
- `prediction`: 0 (benign) or 1 (phishing)
- `probability`: Confidence score from 0.0 to 1.0
- `threshold`: Classification threshold used (default: 0.5)
- `email_id`: ID of created email record (if authenticated)
- `is_phishing`: Boolean indicating if email is classified as phishing

**Error Responses**:
- 400: Invalid request - missing email text
- 500: Error analyzing email

### 2. Analyze Stored Email

**Endpoint**: `POST /api/v1/predictions/analyze-email/{email_id}`

**Authentication**: Required

**Description**: Analyzes a stored email from the database for phishing detection. The email must belong to the authenticated user. The prediction result is saved to the database.

**Path Parameters**:
- `email_id` (integer): The ID of the stored email to analyze

**Request Body**: Empty object `{}`

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
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
  },
  "message": "Email analyzed successfully"
}
```

**Error Responses**:
- 401: Authentication required
- 404: Email not found
- 500: Error analyzing email

## History Endpoints

### 1. Get Prediction History

**Endpoint**: `GET /api/v1/history/predictions`

**Authentication**: Required

**Description**: Retrieves a paginated list of prediction history for the authenticated user. Each prediction includes the email details and prediction results.

**Query Parameters**:
- `limit` (integer, optional): Number of predictions to return (default: 100, min: 1, max: 500)
- `offset` (integer, optional): Number of predictions to skip for pagination (default: 0)

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
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
}
```

**Error Responses**:
- 401: Authentication required
- 500: Error retrieving prediction history

## Error Handling

All API endpoints follow a consistent error response format:

```json
{
  "success": false,
  "error": "Error description",
  "message": "User-friendly error message"
}
```

### HTTP Status Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required or invalid
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error (Pydantic)
- **500 Internal Server Error**: Server error

### Common Error Scenarios

1. **Authentication Required (401)**: 
   - User is not authenticated
   - Session expired
   - OAuth tokens invalid or expired

2. **Access Denied (401/403)**:
   - User trying to access another user's resources
   - Invalid ownership verification

3. **Not Found (404)**:
   - Email ID doesn't exist
   - Resource not found in database

4. **Validation Error (422)**:
   - Invalid request body format
   - Missing required fields
   - Invalid data types

5. **Server Error (500)**:
   - Database connection issues
   - Gmail API errors
   - ML model loading errors
   - Internal processing errors

## Rate Limiting

Currently, the API does not implement rate limiting. However, Gmail API has its own rate limits:
- **Quota**: 1,000,000,000 quota units per day
- **Per-user rate limit**: 250 quota units per user per second

## OAuth2 Scopes

The application requests the following OAuth2 scopes:
- `openid`: OpenID Connect
- `https://www.googleapis.com/auth/userinfo.profile`: User profile information
- `https://www.googleapis.com/auth/userinfo.email`: User email address
- `https://www.googleapis.com/auth/gmail.readonly`: Read-only access to Gmail

## Security

- OAuth tokens are encrypted using Fernet symmetric encryption before storage
- Encryption key is stored in environment variables
- Tokens are never logged or displayed in plain text
- Session-based authentication using secure cookies
- CORS middleware configured for frontend integration

## Data Models

### Email
```json
{
  "id": 1,
  "user_id": 1,
  "gmail_message_id": "abc123",
  "subject": "Email Subject",
  "sender": "sender@example.com",
  "recipient": "recipient@example.com",
  "body": "Email body content",
  "received_at": "2024-01-15T10:30:00Z",
  "received_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Prediction
```json
{
  "id": 1,
  "email_id": 123,
  "prediction": 1,
  "probability": 0.95,
  "model_version": "1.0.0",
  "created_at": "2024-01-15T10:40:00Z"
}
```

## Example Usage

### Complete Authentication Flow

```javascript
// 1. Initiate OAuth2 flow
const response = await fetch('http://localhost:5001/api/v1/auth/connect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({})
});
const data = await response.json();
// Redirect user to data.data.authorization_url

// 2. After callback, check status
const statusResponse = await fetch('http://localhost:5001/api/v1/auth/status', {
  credentials: 'include'
});
const status = await statusResponse.json();
```

### Fetch and Analyze Emails

```javascript
// 1. Fetch emails from Gmail
const fetchResponse = await fetch('http://localhost:5001/api/v1/emails/fetch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ max_results: 50 })
});

// 2. Analyze a stored email
const analyzeResponse = await fetch('http://localhost:5001/api/v1/predictions/analyze-email/123', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({})
});
```

### Manual Email Analysis

```javascript
// Analyze email text directly
const analyzeResponse = await fetch('http://localhost:5001/api/v1/predictions/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    email_text: "Urgent: Verify your bank account immediately"
  })
});
```
