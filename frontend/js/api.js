/**
 * API Client for making requests to the backend API
 */

/**
 * Custom API Error class to distinguish error types
 */
class ApiError extends Error {
  constructor(message, type = "UNKNOWN_ERROR", statusCode = null) {
    super(message);
    this.name = "ApiError";
    this.type = type; // 'AUTH_ERROR', 'NETWORK_ERROR', 'API_ERROR', 'UNKNOWN_ERROR'
    this.statusCode = statusCode;
    this.isAuthError = false;
  }
}

const API_BASE_URL = "http://localhost:5000/api/v1";

class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...options,
      credentials: "include", // Include cookies for session
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    };

    if (config.body && typeof config.body === "object") {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);

      // Handle network errors (fetch failures)
      if (!response) {
        throw new ApiError(
          "Network error: Unable to connect to server. Please check your internet connection.",
          "NETWORK_ERROR",
        );
      }

      // Parse JSON response
      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        // If response is not JSON, create error from status
        throw new ApiError(
          `Server error: ${response.status} ${response.statusText}`,
          "API_ERROR",
          response.status,
        );
      }

      // Handle authentication errors (401, 403)
      if (response.status === 401 || response.status === 403) {
        // Automatically refresh authentication status
        if (window.authManager) {
          await window.authManager.checkStatus();
        }

        // Create authentication error
        const authError = new ApiError(
          data.message ||
            data.error ||
            "Your session has expired. Please reconnect your Gmail account.",
          "AUTH_ERROR",
          response.status,
        );
        authError.isAuthError = true;
        throw authError;
      }

      // Handle other HTTP errors
      if (!response.ok) {
        throw new ApiError(
          data.message ||
            data.error ||
            `Request failed: ${response.status} ${response.statusText}`,
          "API_ERROR",
          response.status,
        );
      }

      return data;
    } catch (error) {
      // Re-throw ApiError as-is
      if (error instanceof ApiError) {
        console.error("API request failed:", error.message, error.type);
        throw error;
      }

      // Handle network errors (fetch throws)
      if (error.name === "TypeError" && error.message.includes("fetch")) {
        console.error("Network error:", error);
        throw new ApiError(
          "Network error: Unable to connect to server. Please check your internet connection.",
          "NETWORK_ERROR",
        );
      }

      // Handle other errors
      console.error("API request failed:", error);
      throw new ApiError(
        error.message || "An unexpected error occurred",
        "UNKNOWN_ERROR",
      );
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: "GET" });
  }

  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: "POST",
      body: data,
    });
  }

  // Auth endpoints
  async checkAuthStatus() {
    return this.get("/auth/status");
  }

  async connectGmail() {
    return this.post("/auth/connect", {});
  }

  async disconnectGmail() {
    return this.post("/auth/disconnect", {});
  }

  // Email endpoints
  async fetchEmails(maxResults = 50) {
    return this.post("/emails/fetch", { max_results: maxResults });
  }

  async getEmails(limit = 50, offset = 0) {
    return this.get(`/emails/list?limit=${limit}&offset=${offset}`);
  }

  async getEmail(emailId) {
    return this.get(`/emails/${emailId}`);
  }

  async getEmailPredictions(emailId) {
    return this.get(`/emails/${emailId}/predictions`);
  }

  // Prediction endpoints
  async analyzeEmail(emailText) {
    return this.post("/predictions/analyze", { email_text: emailText });
  }

  async analyzeStoredEmail(emailId) {
    return this.post(`/predictions/analyze-email/${emailId}`, {});
  }

  // Bulk analysis endpoint
  async analyzeBulkEmails(emailIds) {
    // Analyze emails sequentially using existing endpoint
    const results = {
      successful: [],
      failed: [],
    };

    for (const emailId of emailIds) {
      try {
        const response = await this.analyzeStoredEmail(emailId);
        results.successful.push({ emailId, response });
      } catch (error) {
        results.failed.push({ emailId, error: error.message });
      }
    }

    return results;
  }

  // History endpoints
  async getPredictionHistory(limit = 100, offset = 0) {
    return this.get(`/history/predictions?limit=${limit}&offset=${offset}`);
  }
}

// Export singleton instance
const api = new ApiClient();
window.api = api; // Make available globally
