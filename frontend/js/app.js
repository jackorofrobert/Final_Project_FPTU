/**
 * Main application logic
 */
class App {
    constructor() {
        this.currentPage = 'home';
        this.selectedEmails = new Set(); // Track selected email IDs
        this.emailManagementData = null; // Store email list data
        this.init();
    }

    async init() {
        // Set up authentication state change listener
        authManager.setOnAuthStateChange((isAuthenticated, user) => {
            this.updateNavigation();
            // If user was authenticated and now isn't, show notification
            if (!isAuthenticated && this.currentPage !== 'home') {
                // Don't show error if we're on home page or during initial load
                if (this.currentPage && this.currentPage !== 'home') {
                    this.showError('Your session has expired. Please reconnect your Gmail account to continue.');
                }
            }
        });
        
        // Check authentication status
        await authManager.checkStatus();
        
        // Handle OAuth callback
        this.handleAuthCallback();
        
        // Set up routing
        this.setupRouting();
        
        // Load initial page
        const hash = window.location.hash.substring(1);
        if (hash && hash !== 'auth-success' && hash !== 'auth-error') {
            this.currentPage = hash;
        }
        this.loadPage(this.currentPage);
    }

    handleAuthCallback() {
        const hash = window.location.hash.substring(1);
        if (hash === 'auth-success') {
            this.showSuccess('Successfully connected Gmail account!');
            authManager.checkStatus().then(() => {
                this.updateNavigation();
            });
            window.location.hash = '';
        } else if (hash.startsWith('auth-error=')) {
            const error = decodeURIComponent(hash.substring(11));
            this.showError('Authentication failed: ' + error);
            window.location.hash = '';
        }
    }

    setupRouting() {
        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page) {
                this.loadPage(e.state.page, false);
            }
        });

        // Handle link clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-page]')) {
                e.preventDefault();
                const page = e.target.getAttribute('data-page');
                this.navigate(page);
            }
        });
    }

    navigate(page, pushState = true) {
        if (pushState) {
            window.history.pushState({ page }, '', `#${page}`);
        }
        this.loadPage(page);
    }

    async loadPage(page) {
        this.currentPage = page;
        
        // Show loading
        this.showLoading();

        try {
            switch (page) {
                case 'home':
                    await this.renderHome();
                    break;
                case 'emails':
                    await this.renderEmails();
                    break;
                case 'manage':
                    await this.renderEmailManagement();
                    break;
                case 'analyze':
                    await this.renderAnalyze();
                    break;
                case 'history':
                    await this.renderHistory();
                    break;
                default:
                    await this.renderHome();
            }
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error));
        } finally {
            this.hideLoading();
        }
    }

    async renderHome() {
        const isAuth = authManager.getIsAuthenticated();
        const user = authManager.getUser();

        const html = `
            <div class="hero">
                <h1>Phishing Email Detection System</h1>
                <p>AI-powered email analysis to detect phishing attempts</p>
            </div>

            <div class="features">
                <div class="feature-card">
                    <h3>Connect Gmail</h3>
                    <p>Securely connect your Gmail account to fetch and analyze emails</p>
                    ${isAuth 
                        ? `<span class="badge badge-success">Connected: ${user.email}</span>` 
                        : `<button class="btn btn-primary" onclick="app.connectGmail()">Connect Gmail</button>`
                    }
                </div>

                <div class="feature-card">
                    <h3>Fetch Emails</h3>
                    <p>Retrieve emails from your Gmail account for analysis</p>
                    ${isAuth 
                        ? `<button class="btn btn-primary" onclick="app.fetchEmails()">Fetch Emails</button>` 
                        : `<p class="text-muted">Connect Gmail first</p>`
                    }
                </div>

                <div class="feature-card">
                    <h3>Analyze Email</h3>
                    <p>Manually analyze email content for phishing detection</p>
                    <button class="btn btn-primary" data-page="analyze">Analyze Email</button>
                </div>

                <div class="feature-card">
                    <h3>View History</h3>
                    <p>Review your email analysis history and predictions</p>
                    ${isAuth 
                        ? `<button class="btn btn-primary" data-page="history">View History</button>` 
                        : `<p class="text-muted">Connect Gmail first</p>`
                    }
                </div>
            </div>
        `;

        document.getElementById('app-content').innerHTML = html;
        this.updateNavigation();
    }

    async renderEmails() {
        if (!authManager.getIsAuthenticated()) {
            this.showError('Please connect your Gmail account first');
            this.navigate('home');
            return;
        }

        try {
            const response = await api.getEmails();
            const emails = response.data.emails || [];

            let emailsHtml = '';
            if (emails.length > 0) {
                emailsHtml = `
                    <table class="email-table">
                        <thead>
                            <tr>
                                <th>Subject</th>
                                <th>Sender</th>
                                <th>Date</th>
                                <th>Prediction</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${emails.map(email => `
                                <tr>
                                    <td>${email.subject || '(No Subject)'}</td>
                                    <td>${email.sender || ''}</td>
                                    <td>${email.received_at ? email.received_at.substring(0, 10) : ''}</td>
                                    <td>
                                        ${email.prediction 
                                            ? (email.prediction.prediction == 1 
                                                ? `<span class="badge badge-danger">Phishing</span> <small>(${(email.prediction.probability * 100).toFixed(2)}%)</small>`
                                                : `<span class="badge badge-success">Benign</span> <small>(${(email.prediction.probability * 100).toFixed(2)}%)</small>`)
                                            : `<span class="badge badge-secondary">Not Analyzed</span>`
                                        }
                                    </td>
                                    <td>
                                        <button class="btn btn-sm" onclick="app.viewEmail(${email.id})">View</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } else {
                emailsHtml = '<p class="text-muted">No emails found. <button class="btn btn-primary" onclick="app.fetchEmails()">Fetch emails from Gmail</button></p>';
            }

            document.getElementById('app-content').innerHTML = `
                <h1>Your Emails</h1>
                <div class="email-list">
                    ${emailsHtml}
                </div>
            `;
            this.updateNavigation();
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to load emails'));
            // If it's an auth error, redirect to home
            if (error.isAuthError || error.type === 'AUTH_ERROR') {
                this.navigate('home');
            }
        }
    }

    async renderAnalyze() {
        document.getElementById('app-content').innerHTML = `
            <h1>Analyze Email</h1>
            <div class="analyze-form">
                <form id="analyze-form" onsubmit="app.handleAnalyze(event)">
                    <div class="form-group">
                        <label for="email_text">Email Content:</label>
                        <textarea id="email_text" name="email_text" rows="15" class="form-control" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Analyze</button>
                </form>
            </div>
            <div id="analysis-result"></div>
        `;
        this.updateNavigation();
    }

    async renderHistory() {
        if (!authManager.getIsAuthenticated()) {
            this.showError('Please connect your Gmail account first');
            this.navigate('home');
            return;
        }

        try {
            const response = await api.getPredictionHistory();
            const predictions = response.data.predictions || [];

            let historyHtml = '';
            if (predictions.length > 0) {
                historyHtml = `
                    <table class="history-table">
                        <thead>
                            <tr>
                                <th>Email Subject</th>
                                <th>Sender</th>
                                <th>Prediction</th>
                                <th>Confidence</th>
                                <th>Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${predictions.map(pred => `
                                <tr>
                                    <td>${pred.email ? (pred.email.subject || '(No Subject)') : 'N/A'}</td>
                                    <td>${pred.email ? (pred.email.sender || '') : 'N/A'}</td>
                                    <td>
                                        ${pred.prediction == 1 
                                            ? `<span class="badge badge-danger">Phishing</span>` 
                                            : `<span class="badge badge-success">Benign</span>`
                                        }
                                    </td>
                                    <td>${(pred.probability * 100).toFixed(2)}%</td>
                                    <td>${pred.created_at ? pred.created_at.substring(0, 10) : ''}</td>
                                    <td>
                                        ${pred.email 
                                            ? `<button class="btn btn-sm" onclick="app.viewEmail(${pred.email.id})">View Email</button>` 
                                            : ''
                                        }
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } else {
                historyHtml = '<p class="text-muted">No predictions found. Analyze some emails to see history.</p>';
            }

            document.getElementById('app-content').innerHTML = `
                <h1>Prediction History</h1>
                <div class="history-list">
                    ${historyHtml}
                </div>
            `;
            this.updateNavigation();
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to load history'));
            // If it's an auth error, redirect to home
            if (error.isAuthError || error.type === 'AUTH_ERROR') {
                this.navigate('home');
            }
        }
    }

    async renderEmailManagement() {
        if (!authManager.getIsAuthenticated()) {
            this.showError('Please connect your Gmail account first');
            this.navigate('home');
            return;
        }

        try {
            // Reset selection when loading page
            this.selectedEmails.clear();
            
            const response = await api.getEmails(100, 0); // Get up to 100 emails
            const emails = response.data.emails || [];
            this.emailManagementData = emails;

            // Render email management page
            document.getElementById('app-content').innerHTML = `
                <div class="email-management">
                    <div class="email-management-header">
                        <h1>Email Management</h1>
                        <div class="header-actions">
                            <button class="btn btn-secondary" onclick="app.fetchEmails()">Fetch New Emails</button>
                        </div>
                    </div>
                    
                    <div id="bulk-action-bar" class="bulk-action-bar" style="display: none;">
                        <div class="bulk-action-info">
                            <span id="selected-count">0</span> email(s) selected
                        </div>
                        <div class="bulk-action-buttons">
                            <button class="btn btn-primary btn-sm" onclick="app.analyzeSelectedEmails()">Analyze Selected</button>
                            <button class="btn btn-secondary btn-sm" onclick="app.clearSelection()">Clear Selection</button>
                        </div>
                    </div>

                    <div class="global-actions" style="margin-bottom: 1rem;">
                        <button class="btn btn-primary" onclick="app.analyzeAllEmails()">Analyze All Emails</button>
                    </div>

                    <div class="email-management-content">
                        <div id="analytics-dashboard" class="analytics-dashboard" style="display: none;"></div>
                        
                        <div class="email-list-container">
                            ${this.renderEmailList(emails)}
                        </div>
                    </div>
                </div>
            `;
            
            this.updateNavigation();
            this.updateBulkActionBar();
            this.updateAnalyticsDashboard();
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to load emails'));
            if (error.isAuthError || error.type === 'AUTH_ERROR') {
                this.navigate('home');
            }
        }
    }

    renderEmailList(emails) {
        if (emails.length === 0) {
            return '<p class="text-muted">No emails found. <button class="btn btn-primary" onclick="app.fetchEmails()">Fetch emails from Gmail</button></p>';
        }

        const allSelected = emails.length > 0 && emails.every(email => this.selectedEmails.has(email.id));

        return `
            <table class="email-management-table">
                <thead>
                    <tr>
                        <th style="width: 40px;">
                            <input type="checkbox" id="select-all-checkbox" ${allSelected ? 'checked' : ''} 
                                   onchange="app.toggleSelectAll(this.checked)">
                        </th>
                        <th>Subject</th>
                        <th>Sender</th>
                        <th>Date</th>
                        <th>Prediction</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${emails.map(email => `
                        <tr class="${this.selectedEmails.has(email.id) ? 'selected' : ''}">
                            <td>
                                <input type="checkbox" class="email-checkbox" 
                                       value="${email.id}" 
                                       ${this.selectedEmails.has(email.id) ? 'checked' : ''}
                                       onchange="app.toggleEmailSelection(${email.id}, this.checked)">
                            </td>
                            <td>${email.subject || '(No Subject)'}</td>
                            <td>${email.sender || ''}</td>
                            <td>${email.received_at ? email.received_at.substring(0, 10) : ''}</td>
                            <td>
                                ${email.prediction 
                                    ? (email.prediction.prediction == 1 
                                        ? `<span class="badge badge-danger">Phishing</span> <small>(${(email.prediction.probability * 100).toFixed(2)}%)</small>`
                                        : `<span class="badge badge-success">Benign</span> <small>(${(email.prediction.probability * 100).toFixed(2)}%)</small>`)
                                    : `<span class="badge badge-secondary">Not Analyzed</span>`
                                }
                            </td>
                            <td>
                                <button class="btn btn-sm" onclick="app.viewEmail(${email.id})">View</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    toggleEmailSelection(emailId, isSelected) {
        if (isSelected) {
            this.selectedEmails.add(emailId);
        } else {
            this.selectedEmails.delete(emailId);
        }
        
        // Update row styling
        const row = document.querySelector(`tr:has(input[value="${emailId}"])`);
        if (row) {
            if (isSelected) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
            }
        }
        
        this.updateBulkActionBar();
        this.updateAnalyticsDashboard();
    }

    toggleSelectAll(selectAll) {
        if (!this.emailManagementData) return;
        
        if (selectAll) {
            this.emailManagementData.forEach(email => {
                this.selectedEmails.add(email.id);
            });
        } else {
            this.selectedEmails.clear();
        }
        
        // Update all checkboxes
        document.querySelectorAll('.email-checkbox').forEach(checkbox => {
            checkbox.checked = selectAll;
        });
        
        // Update row styling
        document.querySelectorAll('.email-management-table tbody tr').forEach(row => {
            if (selectAll) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
            }
        });
        
        this.updateBulkActionBar();
        this.updateAnalyticsDashboard();
    }

    clearSelection() {
        this.selectedEmails.clear();
        document.querySelectorAll('.email-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        document.querySelectorAll('#select-all-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        document.querySelectorAll('.email-management-table tbody tr').forEach(row => {
            row.classList.remove('selected');
        });
        this.updateBulkActionBar();
        this.updateAnalyticsDashboard();
    }

    updateBulkActionBar() {
        const bar = document.getElementById('bulk-action-bar');
        const countEl = document.getElementById('selected-count');
        
        if (this.selectedEmails.size > 0) {
            if (bar) bar.style.display = 'flex';
            if (countEl) countEl.textContent = this.selectedEmails.size;
        } else {
            if (bar) bar.style.display = 'none';
        }
    }

    updateAnalyticsDashboard() {
        const dashboard = document.getElementById('analytics-dashboard');
        if (!dashboard || !this.emailManagementData) return;
        
        if (this.selectedEmails.size === 0) {
            dashboard.style.display = 'none';
            return;
        }
        
        // Get selected emails with their data
        const selectedEmailData = this.emailManagementData.filter(email => 
            this.selectedEmails.has(email.id)
        );
        
        // Calculate analytics
        const total = selectedEmailData.length;
        const analyzed = selectedEmailData.filter(email => email.prediction).length;
        const phishing = selectedEmailData.filter(email => 
            email.prediction && email.prediction.prediction == 1
        ).length;
        const benign = selectedEmailData.filter(email => 
            email.prediction && email.prediction.prediction == 0
        ).length;
        const notAnalyzed = total - analyzed;
        
        // Calculate confidence statistics
        const analyzedEmails = selectedEmailData.filter(email => email.prediction);
        const confidences = analyzedEmails.map(email => email.prediction.probability);
        const avgConfidence = confidences.length > 0 
            ? confidences.reduce((a, b) => a + b, 0) / confidences.length 
            : 0;
        const maxConfidence = confidences.length > 0 ? Math.max(...confidences) : 0;
        const minConfidence = confidences.length > 0 ? Math.min(...confidences) : 0;
        const phishingPercentage = analyzed > 0 ? (phishing / analyzed * 100) : 0;
        
        dashboard.style.display = 'block';
        dashboard.innerHTML = `
            <h2>Analytics Dashboard</h2>
            <div class="analytics-grid">
                <div class="analytics-card">
                    <h3>Total Selected</h3>
                    <p class="analytics-value">${total}</p>
                </div>
                <div class="analytics-card">
                    <h3>Phishing</h3>
                    <p class="analytics-value phishing">${phishing}</p>
                    <p class="analytics-percentage">${analyzed > 0 ? phishingPercentage.toFixed(1) : 0}%</p>
                </div>
                <div class="analytics-card">
                    <h3>Benign</h3>
                    <p class="analytics-value benign">${benign}</p>
                    <p class="analytics-percentage">${analyzed > 0 ? (benign / analyzed * 100).toFixed(1) : 0}%</p>
                </div>
                <div class="analytics-card">
                    <h3>Not Analyzed</h3>
                    <p class="analytics-value">${notAnalyzed}</p>
                </div>
                ${analyzed > 0 ? `
                    <div class="analytics-card">
                        <h3>Avg Confidence</h3>
                        <p class="analytics-value">${(avgConfidence * 100).toFixed(2)}%</p>
                    </div>
                    <div class="analytics-card">
                        <h3>Confidence Range</h3>
                        <p class="analytics-value">${(minConfidence * 100).toFixed(2)}% - ${(maxConfidence * 100).toFixed(2)}%</p>
                    </div>
                ` : `
                    <div class="analytics-card full-width">
                        <p class="text-muted">No analyzed emails selected. Click "Analyze Selected" to analyze these emails.</p>
                    </div>
                `}
            </div>
            ${analyzed > 0 ? `
                <div class="analytics-visualization">
                    <h3>Phishing vs Benign Breakdown</h3>
                    <div class="breakdown-bar">
                        <div class="breakdown-segment phishing" style="width: ${phishingPercentage}%">
                            <span>Phishing (${phishing})</span>
                        </div>
                        <div class="breakdown-segment benign" style="width: ${100 - phishingPercentage}%">
                            <span>Benign (${benign})</span>
                        </div>
                    </div>
                </div>
            ` : ''}
        `;
    }

    async analyzeAllEmails() {
        if (!this.emailManagementData || this.emailManagementData.length === 0) {
            this.showError('No emails available to analyze');
            return;
        }
        
        // Select all emails and analyze them
        this.selectedEmails.clear();
        this.emailManagementData.forEach(email => {
            this.selectedEmails.add(email.id);
        });
        
        // Update UI to show all selected
        document.querySelectorAll('.email-checkbox').forEach(checkbox => {
            checkbox.checked = true;
        });
        const selectAllCheckbox = document.getElementById('select-all-checkbox');
        if (selectAllCheckbox) selectAllCheckbox.checked = true;
        document.querySelectorAll('.email-management-table tbody tr').forEach(row => {
            row.classList.add('selected');
        });
        
        this.updateBulkActionBar();
        this.updateAnalyticsDashboard();
        
        // Analyze all emails
        await this.analyzeSelectedEmails();
    }

    async analyzeSelectedEmails() {
        if (this.selectedEmails.size === 0) {
            this.showError('Please select at least one email to analyze');
            return;
        }
        
        const emailIds = Array.from(this.selectedEmails);
        const total = emailIds.length;
        let completed = 0;
        let successful = 0;
        let failed = 0;
        
        try {
            this.showLoading(`Analyzing emails... (0/${total})`);
            
            // Create progress indicator
            const progressHtml = `
                <div id="bulk-analysis-progress" class="bulk-analysis-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 0%"></div>
                    </div>
                    <p>Analyzing ${total} email(s)... <span id="progress-text">0/${total}</span></p>
                </div>
            `;
            const contentEl = document.getElementById('app-content');
            if (contentEl) {
                const existingProgress = document.getElementById('bulk-analysis-progress');
                if (existingProgress) existingProgress.remove();
                contentEl.insertAdjacentHTML('afterbegin', progressHtml);
            }
            
            // Analyze emails sequentially
            for (const emailId of emailIds) {
                try {
                    await api.analyzeStoredEmail(emailId);
                    successful++;
                    
                    // Update email data if available
                    if (this.emailManagementData) {
                        const email = this.emailManagementData.find(e => e.id === emailId);
                        if (email) {
                            // Refresh email data
                            const emailResponse = await api.getEmail(emailId);
                            Object.assign(email, emailResponse.data);
                        }
                    }
                } catch (error) {
                    failed++;
                    console.error(`Failed to analyze email ${emailId}:`, error);
                }
                
                completed++;
                const progress = (completed / total) * 100;
                const progressFill = document.querySelector('.progress-fill');
                const progressText = document.getElementById('progress-text');
                if (progressFill) progressFill.style.width = `${progress}%`;
                if (progressText) progressText.textContent = `${completed}/${total}`;
                this.showLoading(`Analyzing emails... (${completed}/${total})`);
            }
            
            // Remove progress indicator
            const progressEl = document.getElementById('bulk-analysis-progress');
            if (progressEl) progressEl.remove();
            
            // Show results
            if (successful > 0) {
                this.showSuccess(`Successfully analyzed ${successful} email(s)`);
            }
            if (failed > 0) {
                this.showError(`Failed to analyze ${failed} email(s)`);
            }
            
            // Refresh the email list and analytics
            await this.renderEmailManagement();
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to analyze emails'));
        } finally {
            this.hideLoading();
        }
    }

    async connectGmail() {
        try {
            this.showLoading('Connecting to Gmail...');
            await authManager.connectGmail();
            // Note: connectGmail redirects, so this won't execute on success
        } catch (error) {
            this.hideLoading();
            // Error messages from authManager are already user-friendly
            this.showError(error.message || 'Failed to connect Gmail. Please try again.');
        }
    }

    async fetchEmails() {
        try {
            this.showLoading('Fetching emails...');
            const response = await api.fetchEmails();
            this.showSuccess(response.message || 'Emails fetched successfully');
            await this.renderEmails();
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to fetch emails'));
        } finally {
            this.hideLoading();
        }
    }

    async handleAnalyze(event) {
        event.preventDefault();
        const emailText = document.getElementById('email_text').value.trim();
        
        if (!emailText) {
            this.showError('Please enter email content');
            return;
        }

        try {
            this.showLoading('Analyzing email...');
            const response = await api.analyzeEmail(emailText);
            
            const result = response.data;
            const resultHtml = `
                <div class="analysis-result">
                    <h2>Analysis Result</h2>
                    ${result.is_phishing 
                        ? `<div class="alert alert-danger">
                            <strong>⚠️ Phishing Detected!</strong>
                            <p>Confidence: ${(result.probability * 100).toFixed(2)}%</p>
                            <p>Threshold: ${(result.threshold * 100).toFixed(2)}%</p>
                           </div>`
                        : `<div class="alert alert-success">
                            <strong>✓ Benign Email</strong>
                            <p>Confidence: ${(result.probability * 100).toFixed(2)}%</p>
                            <p>Threshold: ${(result.threshold * 100).toFixed(2)}%</p>
                           </div>`
                    }
                </div>
            `;
            document.getElementById('analysis-result').innerHTML = resultHtml;
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to analyze email'));
        } finally {
            this.hideLoading();
        }
    }

    async viewEmail(emailId) {
        try {
            this.showLoading();
            const response = await api.getEmail(emailId);
            const email = response.data;

            const predictionHtml = email.prediction 
                ? (email.prediction.prediction == 1
                    ? `<div class="alert alert-danger">
                        <strong>⚠️ Phishing Detected!</strong>
                        <p>Confidence: ${(email.prediction.probability * 100).toFixed(2)}%</p>
                       </div>`
                    : `<div class="alert alert-success">
                        <strong>✓ Benign Email</strong>
                        <p>Confidence: ${(email.prediction.probability * 100).toFixed(2)}%</p>
                       </div>`)
                : `<div class="prediction-prompt">
                    <p>This email has not been analyzed yet.</p>
                    <button class="btn btn-primary" onclick="app.analyzeStoredEmail(${email.id})">Analyze Email</button>
                   </div>`;

            document.getElementById('app-content').innerHTML = `
                <div class="email-detail">
                    <div class="email-header">
                        <h1>${email.subject || '(No Subject)'}</h1>
                        <div class="email-meta">
                            <p><strong>From:</strong> ${email.sender || ''}</p>
                            <p><strong>To:</strong> ${email.recipient || ''}</p>
                            <p><strong>Date:</strong> ${email.received_at || ''}</p>
                        </div>
                    </div>
                    <div class="email-prediction">
                        ${predictionHtml}
                    </div>
                    <div class="email-body">
                        <h3>Email Content</h3>
                        <div class="email-content">
                            <pre>${email.body || ''}</pre>
                        </div>
                    </div>
                    <div class="email-actions">
                        <button class="btn btn-secondary" data-page="emails">Back to List</button>
                    </div>
                </div>
            `;
            this.updateNavigation();
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to load email'));
            // If it's an auth error, redirect to home
            if (error.isAuthError || error.type === 'AUTH_ERROR') {
                this.navigate('home');
            }
        } finally {
            this.hideLoading();
        }
    }

    async analyzeStoredEmail(emailId) {
        try {
            this.showLoading('Analyzing email...');
            const response = await api.analyzeStoredEmail(emailId);
            this.showSuccess('Email analyzed successfully');
            await this.viewEmail(emailId);
        } catch (error) {
            this.showError(this.getUserFriendlyErrorMessage(error, 'Failed to analyze email'));
        } finally {
            this.hideLoading();
        }
    }

    async disconnectGmail() {
        try {
            this.showLoading('Disconnecting...');
            await authManager.disconnect();
            this.hideLoading();
            this.showSuccess('Gmail account disconnected');
            await this.renderHome();
        } catch (error) {
            this.hideLoading();
            // Error messages from authManager are already user-friendly
            this.showError(error.message || 'Failed to disconnect. Please try again.');
            // Update UI anyway since local state is cleared
            await this.renderHome();
        }
    }

    updateNavigation() {
        const isAuth = authManager.getIsAuthenticated();
        const user = authManager.getUser();

        const navHtml = `
            <a href="#" data-page="home" class="logo">Phishing Detector</a>
            <div class="nav-links">
                <a href="#" data-page="home">Home</a>
                ${isAuth ? `<a href="#" data-page="emails">Emails</a>` : ''}
                ${isAuth ? `<a href="#" data-page="manage">Manage</a>` : ''}
                ${isAuth ? `<a href="#" data-page="history">History</a>` : ''}
                <a href="#" data-page="analyze">Analyze</a>
                ${isAuth 
                    ? `<button class="btn btn-sm" onclick="app.disconnectGmail()">Disconnect</button>
                       <span class="user-email">${user.email}</span>` 
                    : `<button class="btn btn-sm" onclick="app.connectGmail()">Connect Gmail</button>`
                }
            </div>
        `;
        document.querySelector('.navbar .container').innerHTML = navHtml;
    }

    showLoading(message = 'Loading...') {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.textContent = message;
            loadingEl.style.display = 'block';
        }
    }

    hideLoading() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    /**
     * Get user-friendly error message from error object
     */
    getUserFriendlyErrorMessage(error, defaultMessage = 'An error occurred') {
        // Handle ApiError with specific types
        if (error && error.type) {
            switch (error.type) {
                case 'AUTH_ERROR':
                    return 'Your session has expired. Please reconnect your Gmail account to continue.';
                case 'NETWORK_ERROR':
                    return 'Unable to connect to the server. Please check your internet connection and try again.';
                case 'API_ERROR':
                    // Use the error message from API if available
                    return error.message || `${defaultMessage}. Please try again.`;
                default:
                    return error.message || defaultMessage;
            }
        }
        
        // Handle regular Error objects
        if (error && error.message) {
            // Check if it's an authentication-related message
            if (error.message.toLowerCase().includes('session') || 
                error.message.toLowerCase().includes('authenticated') ||
                error.message.toLowerCase().includes('unauthorized')) {
                return 'Your session has expired. Please reconnect your Gmail account to continue.';
            }
            return error.message;
        }
        
        return defaultMessage;
    }

    showMessage(message, type) {
        const messagesEl = document.getElementById('messages');
        if (messagesEl) {
            const messageEl = document.createElement('div');
            messageEl.className = `flash flash-${type}`;
            messageEl.textContent = message;
            messagesEl.appendChild(messageEl);
            
            setTimeout(() => {
                messageEl.remove();
            }, 5000);
        }
    }
}

// Initialize app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new App();
    window.app = app;
});
