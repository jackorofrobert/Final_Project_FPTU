/**
 * Authentication handling module
 */
class AuthManager {
    constructor() {
        this.isAuthenticated = false;
        this.user = null;
        this.onAuthStateChange = null; // Callback for auth state changes
    }

    /**
     * Set callback to be called when authentication state changes
     */
    setOnAuthStateChange(callback) {
        this.onAuthStateChange = callback;
    }

    /**
     * Notify listeners of authentication state change
     */
    _notifyAuthStateChange() {
        if (this.onAuthStateChange) {
            this.onAuthStateChange(this.isAuthenticated, this.user);
        }
    }

    /**
     * Clear authentication state (e.g., when session expires)
     */
    clearAuthState() {
        const wasAuthenticated = this.isAuthenticated;
        this.isAuthenticated = false;
        this.user = null;
        
        // Notify if state changed
        if (wasAuthenticated) {
            this._notifyAuthStateChange();
        }
    }

    async checkStatus() {
        try {
            const response = await api.checkAuthStatus();
            const previousAuthState = this.isAuthenticated;
            
            if (response.success && response.data.authenticated) {
                this.isAuthenticated = true;
                this.user = {
                    id: response.data.user_id,
                    email: response.data.user_email
                };
                
                // Notify if state changed
                if (previousAuthState !== this.isAuthenticated) {
                    this._notifyAuthStateChange();
                }
                return true;
            } else {
                // Session expired or not authenticated
                this.clearAuthState();
                return false;
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            
            // If it's an authentication error, clear state
            if (error.isAuthError || error.type === 'AUTH_ERROR') {
                this.clearAuthState();
            } else {
                // For other errors, just clear state to be safe
                this.clearAuthState();
            }
            return false;
        }
    }

    async connectGmail() {
        try {
            const response = await api.connectGmail();
            if (response.success && response.data.authorization_url) {
                // Redirect to OAuth2 authorization page
                window.location.href = response.data.authorization_url;
            } else {
                throw new Error('Failed to get authorization URL. Please try again.');
            }
        } catch (error) {
            console.error('Gmail connection failed:', error);
            
            // Provide user-friendly error message
            if (error.type === 'NETWORK_ERROR') {
                throw new Error('Unable to connect to server. Please check your internet connection and try again.');
            } else if (error.type === 'AUTH_ERROR') {
                throw new Error('Authentication failed. Please try again.');
            } else {
                throw new Error(error.message || 'Failed to connect Gmail. Please try again.');
            }
        }
    }

    async disconnect() {
        try {
            const response = await api.disconnectGmail();
            if (response.success) {
                this.clearAuthState();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Disconnect failed:', error);
            
            // Even if disconnect fails on server, clear local state
            this.clearAuthState();
            
            // Provide user-friendly error message
            if (error.type === 'NETWORK_ERROR') {
                throw new Error('Unable to disconnect. Please check your internet connection.');
            } else {
                throw new Error(error.message || 'Failed to disconnect. Your local session has been cleared.');
            }
        }
    }

    getUser() {
        return this.user;
    }

    getIsAuthenticated() {
        return this.isAuthenticated;
    }
}

// Export singleton instance
const authManager = new AuthManager();
window.authManager = authManager;
