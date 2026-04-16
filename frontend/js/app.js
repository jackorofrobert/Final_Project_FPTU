/**
 * Main application logic — PhishGuard
 */
class App {
  constructor() {
    this.currentPage = "stats";
    this.selectedEmails = new Set();
    this.emailManagementData = null;
    this.pollInterval = null;
    this.lastKnownEmailCount = null;
    this.init();
  }

  // ──────────────────────────────────────────────────────────────────
  // Initialisation
  // ──────────────────────────────────────────────────────────────────

  async init() {
    authManager.setOnAuthStateChange((isAuthenticated) => {
      if (isAuthenticated) {
        this.hideLoginOverlay();
        this.updateSidebar();
        this.startPolling();
      } else {
        this.showLoginOverlay();
        this.stopPolling();
      }
    });

    await authManager.checkStatus();
    this.setupRouting();

    if (authManager.getIsAuthenticated()) {
      this.hideLoginOverlay();
      this.updateSidebar();
      const hash = window.location.hash.substring(1);
      if (hash.startsWith("email/")) {
        const emailId = parseInt(hash.split("/")[1], 10);
        if (!isNaN(emailId)) { this.viewEmail(emailId); this.startPolling(); return; }
      }
      const validPages = ["stats", "emails", "manage", "analyze", "history", "fetch-history"];
      const page = validPages.includes(hash) ? hash : "stats";
      this.loadPage(page);
      this.startPolling();
    } else {
      this.showLoginOverlay();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Login Overlay
  // ──────────────────────────────────────────────────────────────────

  showLoginOverlay() {
    const overlay = document.getElementById("login-overlay");
    const shell = document.getElementById("app-shell");
    if (overlay) overlay.style.display = "flex";
    if (shell) shell.style.display = "none";
  }

  hideLoginOverlay() {
    const overlay = document.getElementById("login-overlay");
    const shell = document.getElementById("app-shell");
    if (overlay) overlay.style.display = "none";
    if (shell) shell.style.display = "flex";
  }

  async handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    const errorEl = document.getElementById("login-error");
    const btn = document.getElementById("login-btn");

    if (errorEl) errorEl.style.display = "none";
    if (btn) { btn.disabled = true; btn.textContent = "Signing in…"; }

    try {
      await authManager.connect(email, password);
      this.hideLoginOverlay();
      this.updateSidebar();
      this.loadPage("stats");
      this.startPolling();
    } catch (error) {
      if (errorEl) {
        errorEl.textContent = error.message || "Sign in failed. Please check your credentials.";
        errorEl.style.display = "block";
      }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Sign In"; }
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Sidebar
  // ──────────────────────────────────────────────────────────────────

  toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const shell = document.getElementById("app-shell");
    if (!sidebar) return;
    if (window.innerWidth <= 900) {
      sidebar.classList.toggle("mobile-open");
      shell.classList.toggle("sidebar-open");
    } else {
      sidebar.classList.toggle("collapsed");
    }
  }

  updateSidebar() {
    const isAuth = authManager.getIsAuthenticated();
    const user = authManager.getUser();
    const navEl = document.getElementById("sidebar-nav");
    const footerEl = document.getElementById("sidebar-footer");
    if (!navEl || !footerEl) return;

    const NAV_ITEMS = [
      { page: "stats",         icon: "📊", label: "Dashboard" },
      { page: "emails",        icon: "📧", label: "Emails" },
      { page: "manage",        icon: "⚙️", label: "Manage" },
      { page: "analyze",       icon: "🔍", label: "Analyze" },
      { page: "history",       icon: "📋", label: "History" },
      { page: "fetch-history", icon: "🔄", label: "Sync Log" },
    ];

    navEl.innerHTML = NAV_ITEMS.map((item) => `
      <a href="#" data-page="${item.page}" class="${this.currentPage === item.page ? "active" : ""}">
        <span class="nav-icon">${item.icon}</span>
        <span class="nav-label">${item.label}</span>
      </a>
    `).join("");

    if (isAuth && user) {
      const initials = user.email ? user.email[0].toUpperCase() : "?";
      footerEl.innerHTML = `
        <div class="sidebar-user">
          <div class="sidebar-user-avatar">${initials}</div>
          <div class="sidebar-user-info">
            <span class="sidebar-user-email" title="${user.email}">${user.email}</span>
          </div>
        </div>
        <button class="sidebar-disconnect-btn" onclick="app.disconnectAccount()">
          <span style="font-size:13px">→</span>
          <span class="nav-label">Sign Out</span>
        </button>
      `;
    } else {
      footerEl.innerHTML = "";
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Polling
  // ──────────────────────────────────────────────────────────────────

  startPolling() {
    if (this.pollInterval) return;
    this.pollForNewEmails();
    this.pollInterval = setInterval(() => this.pollForNewEmails(), 30000);
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  async pollForNewEmails() {
    try {
      const response = await api.getFetchStatus();
      const { total_emails, last_fetch_at } = response.data;

      if (this.lastKnownEmailCount !== null && total_emails > this.lastKnownEmailCount) {
        const newCount = total_emails - this.lastKnownEmailCount;
        this.showNewEmailNotification(newCount);
        if (this.currentPage === "emails" || this.currentPage === "manage") {
          this.loadPage(this.currentPage);
        }
      }
      this.lastKnownEmailCount = total_emails;
      this.updateFetchStatusIndicator(last_fetch_at);
    } catch (e) {
      // silently ignore poll errors
    }
  }

  showNewEmailNotification(count) {
    const container = document.getElementById("messages");
    if (!container) return;
    const el = document.createElement("div");
    el.className = "flash flash-info new-email-notification";
    el.innerHTML = `<strong>${count} new email${count > 1 ? "s" : ""}</strong> fetched.
      <button class="btn btn-sm" style="margin-left:12px" onclick="app.navigate('emails'); this.parentElement.remove();">View</button>`;
    container.appendChild(el);
    setTimeout(() => el.remove(), 8000);
  }

  updateFetchStatusIndicator(lastFetchAt) {
    const el = document.getElementById("fetch-status-time");
    if (!el) return;
    if (lastFetchAt) {
      const d = new Date(lastFetchAt);
      el.textContent = `Last sync: ${d.toLocaleTimeString()}`;
    } else {
      el.textContent = "Not synced yet";
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Routing
  // ──────────────────────────────────────────────────────────────────

  setupRouting() {
    window.addEventListener("popstate", (e) => {
      if (e.state && e.state.page) {
        if (e.state.page.startsWith("email/")) {
          const emailId = parseInt(e.state.page.split("/")[1], 10);
          if (!isNaN(emailId)) { this.viewEmail(emailId); return; }
        }
        this.loadPage(e.state.page, false);
      }
    });

    document.addEventListener("click", (e) => {
      const target = e.target.closest("[data-page]");
      if (target) {
        e.preventDefault();
        const page = target.getAttribute("data-page");
        this.navigate(page);
      }
    });

    // Close mobile sidebar on content click
    document.addEventListener("click", (e) => {
      const sidebar = document.getElementById("sidebar");
      const shell = document.getElementById("app-shell");
      if (
        sidebar &&
        sidebar.classList.contains("mobile-open") &&
        !sidebar.contains(e.target) &&
        !e.target.closest(".topbar-menu-btn")
      ) {
        sidebar.classList.remove("mobile-open");
        shell.classList.remove("sidebar-open");
      }
    });
  }

  navigate(page, pushState = true) {
    if (pushState) {
      window.history.pushState({ page }, "", `#${page}`);
    }
    this.loadPage(page);
  }

  async loadPage(page) {
    this.currentPage = page;
    this.showLoading();
    // Update active state in sidebar
    document.querySelectorAll("#sidebar-nav a").forEach((a) => {
      a.classList.toggle("active", a.getAttribute("data-page") === page);
    });

    try {
      switch (page) {
        case "stats":         await this.renderStats();         break;
        case "emails":        await this.renderEmails();        break;
        case "manage":        await this.renderEmailManagement(); break;
        case "analyze":       await this.renderAnalyze();       break;
        case "history":       await this.renderHistory();       break;
        case "fetch-history": await this.renderFetchHistory();  break;
        default:              await this.renderStats();
      }
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error));
    } finally {
      this.hideLoading();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Stats Dashboard
  // ──────────────────────────────────────────────────────────────────

  async renderStats() {
    if (!authManager.getIsAuthenticated()) {
      this.showLoginOverlay();
      return;
    }

    document.getElementById("app-content").innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Dashboard</h1>
          <p class="page-subtitle">Overview of your email security analysis</p>
        </div>
        <div class="page-actions">
          <button class="btn btn-secondary btn-sm" onclick="app.loadPage('stats')">Refresh</button>
          <button class="btn btn-primary btn-sm" onclick="app.fetchEmails()">Fetch Emails</button>
        </div>
      </div>
      <div class="stat-grid" id="stat-grid-placeholder">
        ${Array(5).fill(0).map(() => `<div class="stat-card"><div class="stat-card-label">…</div><div class="stat-card-value" style="color:var(--border)">—</div></div>`).join("")}
      </div>
      <div id="stats-lower"><p class="text-muted" style="text-align:center;padding:32px 0;">Loading statistics…</p></div>
    `;

    try {
      const [overviewRes, classRes, sendersRes, trendRes, domainsRes, featuresRes, segmentsRes, linksRes, timelineRes, probDistRes] = await Promise.all([
        api.getStatsOverview(),
        api.getStatsClassification(),
        api.getStatsTopSenders(8),
        api.getStatsTrend(14),
        api.getStatsTopDomains(8),
        api.getStatsFeatures(),
        api.getStatsSegments(),
        api.getStatsLinks(8),
        api.getStatsTimeline(30),
        api.getStatsProbabilityDist(),
      ]);

      const ov       = overviewRes.data;
      const cl       = classRes.data;
      const senders  = sendersRes.data.senders || [];
      const trend    = trendRes.data.data || [];
      const domains  = domainsRes.data.domains || [];
      const features = featuresRes.data || {};
      const segments = segmentsRes.data || {};
      const links    = linksRes.data || {};
      const timeline = timelineRes.data.data || [];
      const probDist = probDistRes.data.buckets || [];

      // ── Stat cards ──────────────────────────────────────────────
      const statGridHtml = `
        <div class="stat-card">
          <div class="stat-card-label">Total Emails</div>
          <div class="stat-card-value primary">${ov.emails.total}</div>
          <div class="stat-card-sub">${ov.emails.analyzed} analyzed · ${ov.emails.unanalyzed} pending</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Phishing Detected</div>
          <div class="stat-card-value danger">${ov.threats.phishing}</div>
          <div class="stat-card-sub">Threat rate: ${ov.threats.threat_rate}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Suspicious</div>
          <div class="stat-card-value warning">${ov.threats.suspicious}</div>
          <div class="stat-card-sub">Needs review</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">Legitimate</div>
          <div class="stat-card-value success">${ov.threats.legitimate}</div>
          <div class="stat-card-sub">Safe emails</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-label">VT Links Scanned</div>
          <div class="stat-card-value info">${ov.virustotal.total_links}</div>
          <div class="stat-card-sub">${ov.virustotal.malicious_links} malicious · ${ov.virustotal.suspicious_links} suspicious</div>
        </div>
      `;

      // ── Classification breakdown bar ─────────────────────────────
      const breakdown     = cl.breakdown || [];
      const phishingData  = breakdown.find((r) => r.classification === "PHISHING")   || { count: 0, pct: 0 };
      const suspiciousData= breakdown.find((r) => r.classification === "SUSPICIOUS") || { count: 0, pct: 0 };
      const legitimateData= breakdown.find((r) => r.classification === "LEGITIMATE") || { count: 0, pct: 0 };
      const unanalyzedData= breakdown.find((r) => r.classification === "UNANALYZED") || { count: 0, pct: 0 };

      const seg = (cls, data) =>
        data.pct > 0
          ? `<div class="classification-segment ${cls}" style="width:${data.pct}%">${data.pct > 9 ? data.pct + "%" : ""}</div>`
          : "";

      const classCardHtml = `
        <div class="card">
          <div class="card-header">
            <span class="card-title">Classification Breakdown</span>
            <span class="text-muted" style="font-size:0.78rem">${cl.total} analyzed</span>
          </div>
          <div class="card-body">
            <div class="classification-bar">
              ${seg("phishing",   phishingData)}
              ${seg("suspicious", suspiciousData)}
              ${seg("legitimate", legitimateData)}
              ${seg("unanalyzed", unanalyzedData)}
            </div>
            <div class="classification-legend">
              <div class="legend-item"><span class="legend-dot phishing"></span>Phishing: ${phishingData.count} (${phishingData.pct}%)</div>
              <div class="legend-item"><span class="legend-dot suspicious"></span>Suspicious: ${suspiciousData.count} (${suspiciousData.pct}%)</div>
              <div class="legend-item"><span class="legend-dot legitimate"></span>Legitimate: ${legitimateData.count} (${legitimateData.pct}%)</div>
              ${unanalyzedData.count > 0 ? `<div class="legend-item"><span class="legend-dot unanalyzed"></span>Unanalyzed: ${unanalyzedData.count}</div>` : ""}
            </div>
          </div>
        </div>
      `;

      // ── Top senders ──────────────────────────────────────────────
      const maxSenderTotal = senders.length > 0 ? Math.max(...senders.map((s) => s.total)) : 1;
      const sendersHtml = `
        <div class="card">
          <div class="card-header"><span class="card-title">Top Senders</span></div>
          <div class="card-body" style="padding-bottom:12px">
            ${senders.length === 0
              ? '<p class="text-muted">No sender data yet.</p>'
              : senders.map((s) => {
                  const pct = Math.max(4, Math.round((s.total / maxSenderTotal) * 100));
                  const risky = (s.phishing_count || s.phishing || 0) > 0 || (s.suspicious_count || s.suspicious || 0) > 0;
                  return `
                    <div class="bar-chart-row">
                      <div class="bar-chart-label" title="${this.escapeHtml(s.sender || "")}">${this.escapeHtml(s.sender || "")}</div>
                      <div class="bar-chart-track">
                        <div class="bar-chart-fill ${risky ? "danger" : "success"}" style="width:${pct}%">${s.total_emails || s.total}</div>
                      </div>
                    </div>
                  `;
                }).join("")
            }
          </div>
        </div>
      `;

      // ── Top domains ──────────────────────────────────────────────
      const maxDomainTotal = domains.length > 0 ? Math.max(...domains.map((d) => d.total)) : 1;
      const domainsHtml = `
        <div class="card">
          <div class="card-header"><span class="card-title">Top Sender Domains</span></div>
          <div class="card-body" style="padding-bottom:12px">
            ${domains.length === 0
              ? '<p class="text-muted">No domain data yet.</p>'
              : domains.map((d) => {
                  const pct = Math.max(4, Math.round((d.total / maxDomainTotal) * 100));
                  const risky = (d.phishing_count || 0) > 0 || (d.suspicious_count || 0) > 0;
                  return `
                    <div class="bar-chart-row">
                      <div class="bar-chart-label" title="${this.escapeHtml(d.sender_domain || "")}">${this.escapeHtml(d.sender_domain || "(unknown)")}</div>
                      <div class="bar-chart-track">
                        <div class="bar-chart-fill ${risky ? "danger" : "success"}" style="width:${pct}%">${d.total}</div>
                      </div>
                    </div>
                  `;
                }).join("")
            }
          </div>
        </div>
      `;

      // ── 14-day activity trend ─────────────────────────────────────
      const last14 = trend.slice(-14);
      const maxDay = last14.length > 0
        ? Math.max(...last14.map((r) => (r.phishing || 0) + (r.suspicious || 0) + (r.legitimate || 0) + (r.unanalyzed || 0)), 1)
        : 1;

      const trendHtml = `
        <div class="card" style="grid-column: 1 / -1">
          <div class="card-header"><span class="card-title">14-Day Activity Trend</span></div>
          <div class="card-body" style="padding-bottom:12px">
            ${last14.length === 0
              ? '<p class="text-muted">No trend data yet.</p>'
              : last14.map((r) => {
                  const total = (r.phishing || 0) + (r.suspicious || 0) + (r.legitimate || 0) + (r.unanalyzed || 0);
                  const pct = Math.max(2, Math.round((total / maxDay) * 100));
                  const date = r.date ? r.date.substring(5) : "";
                  const risky = (r.phishing || 0) + (r.suspicious || 0) > 0;
                  return `
                    <div class="bar-chart-row">
                      <div class="bar-chart-label">${date}</div>
                      <div class="bar-chart-track">
                        <div class="bar-chart-fill ${risky ? "warning" : "info"}" style="width:${pct}%">${total}</div>
                      </div>
                    </div>
                  `;
                }).join("")
            }
          </div>
        </div>
      `;

      // ── Feature stats ─────────────────────────────────────────────
      const riskBreakdown = features.sender_risk_breakdown || [];
      const linksDist     = features.links_count_distribution || [];
      const maxRiskCount  = riskBreakdown.length > 0 ? Math.max(...riskBreakdown.map((r) => r.count)) : 1;
      const maxLinksCount = linksDist.length > 0 ? Math.max(...linksDist.map((r) => r.count)) : 1;
      const featuresHtml = `
        <div class="card">
          <div class="card-header"><span class="card-title">Email Feature Analysis</span></div>
          <div class="card-body">
            <div class="stats-feature-grid">
              <div class="stats-feature-item">
                <div class="stats-feature-value">${features.avg_links_count ?? 0}</div>
                <div class="stats-feature-label">Avg Links</div>
              </div>
              <div class="stats-feature-item">
                <div class="stats-feature-value">${features.max_links_count ?? 0}</div>
                <div class="stats-feature-label">Max Links</div>
              </div>
              <div class="stats-feature-item">
                <div class="stats-feature-value">${features.emails_with_attachment_pct ?? 0}%</div>
                <div class="stats-feature-label">Attachment</div>
              </div>
              <div class="stats-feature-item">
                <div class="stats-feature-value">${features.emails_with_urgent_keywords_pct ?? 0}%</div>
                <div class="stats-feature-label">Urgent Lang</div>
              </div>
            </div>
            ${riskBreakdown.length > 0 ? `
              <p class="stats-section-label" style="margin-top:14px">Sender Risk</p>
              ${riskBreakdown.map((r) => {
                const pct = Math.max(4, Math.round(r.count / maxRiskCount * 100));
                const cls = r.sender_risk === "HIGH" ? "danger" : r.sender_risk === "MEDIUM" ? "warning" : "success";
                return `<div class="bar-chart-row">
                  <div class="bar-chart-label">${r.sender_risk}</div>
                  <div class="bar-chart-track">
                    <div class="bar-chart-fill ${cls}" style="width:${pct}%">${r.count}</div>
                  </div>
                </div>`;
              }).join("")}
            ` : ""}
            ${linksDist.length > 0 ? `
              <p class="stats-section-label" style="margin-top:14px">Links per Email</p>
              ${linksDist.map((r) => {
                const pct = Math.max(4, Math.round(r.count / maxLinksCount * 100));
                return `<div class="bar-chart-row">
                  <div class="bar-chart-label" style="font-family:monospace">${r.bucket}</div>
                  <div class="bar-chart-track">
                    <div class="bar-chart-fill info" style="width:${pct}%">${r.count}</div>
                  </div>
                </div>`;
              }).join("")}
            ` : ""}
          </div>
        </div>
      `;

      // ── Link risk stats ───────────────────────────────────────────
      const topMalicious = links.top_malicious || [];
      const linksHtml = `
        <div class="card">
          <div class="card-header">
            <span class="card-title">Link Risk Analysis</span>
            <span class="text-muted" style="font-size:0.78rem">${links.total_links || 0} links total</span>
          </div>
          <div class="card-body">
            <div class="stats-feature-grid" style="margin-bottom:14px">
              <div class="stats-feature-item">
                <div class="stats-feature-value" style="color:var(--danger)">${links.malicious_links || 0}</div>
                <div class="stats-feature-label">Malicious</div>
              </div>
              <div class="stats-feature-item">
                <div class="stats-feature-value" style="color:var(--warning)">${links.suspicious_links || 0}</div>
                <div class="stats-feature-label">Suspicious</div>
              </div>
              <div class="stats-feature-item">
                <div class="stats-feature-value" style="color:var(--success)">${links.clean_links || 0}</div>
                <div class="stats-feature-label">Clean</div>
              </div>
            </div>
            ${topMalicious.length > 0 ? `
              <p class="stats-section-label">Top Malicious URLs</p>
              <div class="table-scroll" style="margin-top:6px">
                <table class="fetch-history-table">
                  <thead><tr><th>Domain</th><th>Type</th><th>Risk</th></tr></thead>
                  <tbody>
                    ${topMalicious.map((r) => `
                      <tr>
                        <td class="vt-url-cell">${this.escapeHtml(r.domain || r.url || "")}</td>
                        <td><span class="badge badge-warning">${r.link_type || ""}</span></td>
                        <td><span class="badge badge-danger">${(r.risk_score * 100).toFixed(0)}%</span></td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            ` : '<p class="text-muted">No malicious links detected.</p>'}
          </div>
        </div>
      `;

      // ── Suspicious segments ───────────────────────────────────────
      const sevBreakdown = segments.severity_breakdown || [];
      const topSegs      = segments.top_segments || [];
      const segmentsHtml = `
        <div class="card">
          <div class="card-header"><span class="card-title">Suspicious Text Segments</span></div>
          <div class="card-body">
            ${sevBreakdown.length === 0 && topSegs.length === 0
              ? '<p class="text-muted">No suspicious segments found.</p>'
              : `
                ${sevBreakdown.length > 0 ? `
                  <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
                    ${sevBreakdown.map((s) => {
                      const cls = s.severity === "HIGH" ? "badge-danger" : s.severity === "MEDIUM" ? "badge-warning" : "badge-info";
                      return `<div class="stats-severity-pill ${cls}">
                        <strong>${s.severity}</strong>
                        <span>${s.count} · avg ${s.avg_score}%</span>
                      </div>`;
                    }).join("")}
                  </div>
                ` : ""}
                ${topSegs.slice(0, 5).map((s) => {
                  const cls = s.severity === "HIGH" ? "danger" : s.severity === "MEDIUM" ? "warning" : "info";
                  const subj = (s.subject || "").substring(0, 40);
                  const text = (s.text || "").substring(0, 120);
                  return `
                    <div class="stats-segment-item">
                      <div class="stats-segment-header">
                        <span class="badge badge-${cls}">${s.severity}</span>
                        <span class="stats-segment-score">${s.score}%</span>
                        <span class="text-muted" style="font-size:0.72rem;margin-left:auto" title="${this.escapeHtml(s.subject || "")}">${this.escapeHtml(subj)}${(s.subject || "").length > 40 ? "…" : ""}</span>
                      </div>
                      <div class="stats-segment-text">${this.escapeHtml(text)}${(s.text || "").length > 120 ? "…" : ""}</div>
                    </div>
                  `;
                }).join("")}
              `
            }
          </div>
        </div>
      `;

      // ── 30-day receive timeline ───────────────────────────────────
      const maxVol = timeline.length > 0 ? Math.max(...timeline.map((r) => r.email_count), 1) : 1;
      const timelineHtml = `
        <div class="card" style="grid-column: 1 / -1">
          <div class="card-header"><span class="card-title">30-Day Receive Volume</span></div>
          <div class="card-body" style="padding-bottom:12px">
            ${timeline.length === 0
              ? '<p class="text-muted">No receive volume data yet.</p>'
              : timeline.map((r) => {
                  const pct = Math.max(2, Math.round((r.email_count / maxVol) * 100));
                  const date = r.date ? r.date.substring(5) : "";
                  return `
                    <div class="bar-chart-row">
                      <div class="bar-chart-label">${date}</div>
                      <div class="bar-chart-track">
                        <div class="bar-chart-fill primary" style="width:${pct}%">${r.email_count}</div>
                      </div>
                    </div>
                  `;
                }).join("")
            }
          </div>
        </div>
      `;

      // ── ML confidence score distribution ─────────────────────────
      const probDistHtml = `
        <div class="card" style="grid-column: 1 / -1">
          <div class="card-header"><span class="card-title">ML Confidence Score Distribution</span></div>
          <div class="card-body" style="padding-bottom:12px">
            ${probDist.length === 0
              ? '<p class="text-muted">No analysis data yet.</p>'
              : probDist.map((r) => {
                  const barPct = Math.max(r.pct, 2);
                  const bucketStart = parseFloat(r.bucket.split("-")[0]);
                  const cls = bucketStart >= 0.7 ? "danger" : bucketStart >= 0.5 ? "warning" : "success";
                  return `
                    <div class="bar-chart-row">
                      <div class="bar-chart-label" style="font-family:monospace">${r.bucket}</div>
                      <div class="bar-chart-track">
                        <div class="bar-chart-fill ${cls}" style="width:${barPct}%">${r.count} (${r.pct}%)</div>
                      </div>
                    </div>
                  `;
                }).join("")
            }
          </div>
        </div>
      `;

      document.getElementById("app-content").innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Dashboard</h1>
            <p class="page-subtitle">Overview of your email security analysis</p>
          </div>
          <div class="page-actions">
            <button class="btn btn-secondary btn-sm" onclick="app.loadPage('stats')">Refresh</button>
            <button class="btn btn-primary btn-sm" onclick="app.fetchEmails()">Fetch Emails</button>
          </div>
        </div>
        <div class="stat-grid">${statGridHtml}</div>
        ${classCardHtml}
        <div class="content-grid" style="margin-top:16px">
          ${sendersHtml}
          ${domainsHtml}
          ${trendHtml}
        </div>
        <div class="content-grid" style="margin-top:16px">
          ${featuresHtml}
          ${linksHtml}
          ${segmentsHtml}
        </div>
        <div class="content-grid" style="margin-top:16px">
          ${timelineHtml}
          ${probDistHtml}
        </div>
      `;

      this.updateSidebar();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to load statistics"));
      if (error.isAuthError || error.type === "AUTH_ERROR") {
        this.showLoginOverlay();
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Emails Page
  // ──────────────────────────────────────────────────────────────────

  async renderEmails() {
    if (!authManager.getIsAuthenticated()) {
      this.showLoginOverlay();
      return;
    }

    try {
      const response = await api.getEmails();
      const emails = response.data.emails || [];

      let emailsHtml = "";
      if (emails.length > 0) {
        emailsHtml = `
          <div class="table-scroll">
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
                ${emails.map((email) => `
                  <tr>
                    <td>${email.subject || "(No Subject)"}</td>
                    <td>${email.sender || ""}</td>
                    <td>${email.received_at ? email.received_at.substring(0, 10) : ""}</td>
                    <td>${this.renderPredictionBadge(email.prediction, email.vt_summary)}</td>
                    <td><button class="btn btn-sm btn-secondary" onclick="app.viewEmail(${email.id})">View</button></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `;
      } else {
        emailsHtml = `
          <div class="empty-state">
            <p>No emails found.</p>
            <button class="btn btn-primary" onclick="app.fetchEmails()">Fetch Emails</button>
          </div>
        `;
      }

      document.getElementById("app-content").innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Emails</h1>
            <p class="page-subtitle">${emails.length} email${emails.length !== 1 ? "s" : ""} in your inbox</p>
          </div>
          <div class="page-actions">
            <button class="btn btn-primary btn-sm" onclick="app.fetchEmails()">Fetch New</button>
          </div>
        </div>
        <div class="table-container">${emailsHtml}</div>
      `;
      this.updateSidebar();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to load emails"));
      if (error.isAuthError || error.type === "AUTH_ERROR") {
        this.showLoginOverlay();
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Analyze Page
  // ──────────────────────────────────────────────────────────────────

  async renderAnalyze() {
    document.getElementById("app-content").innerHTML = `
      <div class="page-header">
        <div>
          <h1 class="page-title">Analyze Email</h1>
          <p class="page-subtitle">Paste email content, translate if needed, then run the ML model</p>
        </div>
      </div>

      <div class="dual-panel">
        <!-- LEFT: Original text -->
        <div class="panel-card">
          <div class="panel-card-header">
            <span class="panel-label">Original</span>
            <div class="panel-card-actions">
              <button type="button" class="btn btn-sm btn-secondary" onclick="app.translateAnalyzeTextToEnglish()">
                Translate to English →
              </button>
              <button type="button" class="btn btn-sm btn-primary" onclick="app.submitAnalyzeForm()">
                Analyze Original
              </button>
            </div>
          </div>
          <div class="panel-card-body">
            <textarea
              id="email_text"
              rows="16"
              class="form-control"
              placeholder="Paste the full email text here…"
              style="min-height:280px"
            ></textarea>
            <div style="margin-top:8px;min-height:1.2rem">
              <span id="analyze-translate-status" class="panel-meta"></span>
            </div>
          </div>
          <div id="original-analysis-result" class="panel-analysis-result"></div>
        </div>

        <!-- RIGHT: English translation -->
        <div class="panel-card">
          <div class="panel-card-header">
            <span class="panel-label panel-label-en">English Translation</span>
            <div class="panel-card-actions" id="analyze-translation-actions" style="display:none">
              <span class="panel-saved-badge">✓ Translated</span>
              <span class="panel-meta" id="analyze-translation-meta"></span>
              <button type="button" class="btn btn-sm btn-primary" onclick="app.analyzeTranslatedPasteWithML()">
                Analyze Translation
              </button>
            </div>
          </div>
          <div class="panel-card-body">
            <div id="analyze-translation-empty" class="panel-empty-state">
              <div class="panel-empty-icon">🌐</div>
              <div>
                <strong>No translation yet</strong><br>
                <span style="font-size:0.8rem">Click "Translate to English →" on the left to generate one.</span>
              </div>
            </div>
            <pre id="analyze-translation-text" style="display:none"></pre>
          </div>
          <div id="translation-analysis-result" class="panel-analysis-result"></div>
        </div>
      </div>
    `;
    this.updateSidebar();
  }

  submitAnalyzeForm() {
    const text = (document.getElementById("email_text")?.value || "").trim();
    if (!text) { this.showError("Please enter some email text first."); return; }
    this.handleAnalyze({ preventDefault: () => {} }, { emailText: text, targetId: "original-analysis-result" });
  }

  // ──────────────────────────────────────────────────────────────────
  // History Page
  // ──────────────────────────────────────────────────────────────────

  async renderHistory() {
    if (!authManager.getIsAuthenticated()) {
      this.showLoginOverlay();
      return;
    }

    try {
      const response = await api.getPredictionHistory();
      const predictions = response.data.predictions || [];

      let historyHtml = "";
      if (predictions.length > 0) {
        historyHtml = `
          <div class="table-scroll">
            <table class="history-table">
              <thead>
                <tr>
                  <th>Email Subject</th>
                  <th>Sender</th>
                  <th>Prediction</th>
                  <th>ML Input</th>
                  <th>Confidence</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${predictions.map((pred) => `
                  <tr>
                    <td>${pred.email ? pred.email.subject || "(No Subject)" : "N/A"}</td>
                    <td>${pred.email ? pred.email.sender || "" : "N/A"}</td>
                    <td>${this.renderPredictionBadge(pred)}</td>
                    <td>${this.renderInputSourceLabel(pred.input_source)}</td>
                    <td>${(pred.probability * 100).toFixed(2)}%</td>
                    <td>${pred.created_at ? pred.created_at.substring(0, 10) : ""}</td>
                    <td>
                      ${pred.email ? `<button class="btn btn-sm btn-secondary" onclick="app.viewEmail(${pred.email.id})">View</button>` : ""}
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `;
      } else {
        historyHtml = `<div class="empty-state"><p>No predictions yet. Analyze some emails to see history.</p></div>`;
      }

      document.getElementById("app-content").innerHTML = `
        <div class="page-header">
          <div>
            <h1 class="page-title">Prediction History</h1>
            <p class="page-subtitle">${predictions.length} prediction${predictions.length !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div class="table-container">${historyHtml}</div>
      `;
      this.updateSidebar();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to load history"));
      if (error.isAuthError || error.type === "AUTH_ERROR") {
        this.showLoginOverlay();
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Fetch History / Sync Log Page
  // ──────────────────────────────────────────────────────────────────

  async renderFetchHistory() {
    if (!authManager.getIsAuthenticated()) {
      this.showLoginOverlay();
      return;
    }

    try {
      const [
        statusRes,
        logsRes,
        analysisStatusRes,
        analysisLogsRes,
        vtStatusRes,
        vtLogsRes,
        vtResultsRes,
        translationStatusRes,
        translationHistoryRes,
      ] = await Promise.all([
        api.getFetchStatus(),
        api.getFetchHistory(50, 0),
        api.getAnalysisStatus(),
        api.getAnalysisHistory(50, 0),
        api.getVTStatus(),
        api.getVTHistory(50, 0),
        api.getVTResults(100, 0),
        api.getTranslationStatus(),
        api.getTranslationHistory(50, 0),
      ]);

      const { last_fetch_at, total_emails } = statusRes.data;
      const logs            = logsRes.data.logs || [];
      const { last_analysis_at, unanalyzed_count } = analysisStatusRes.data;
      const analysisLogs    = analysisLogsRes.data.logs || [];
      const vtUsage         = vtStatusRes.data;
      const vtLogs          = vtLogsRes.data.logs || [];
      const vtResults       = vtResultsRes.data.results || [];
      const trStats         = translationStatusRes.data || {};
      const translationLogs = translationHistoryRes.data.logs || [];

      const lastSync     = last_fetch_at     ? new Date(last_fetch_at).toLocaleString()     : "Never";
      const lastAnalysis = last_analysis_at  ? new Date(last_analysis_at).toLocaleString()  : "Never";

      // Fetch history table
      let fetchLogsHtml = "";
      if (logs.length > 0) {
        fetchLogsHtml = `
          <table class="fetch-history-table">
            <thead><tr><th>Time</th><th>Source</th><th>Fetched</th><th>New</th></tr></thead>
            <tbody>
              ${logs.map((log) => {
                const time = log.created_at ? new Date(log.created_at).toLocaleString() : "";
                const srcBadge = log.source === "scheduler"
                  ? `<span class="badge badge-info">Auto</span>`
                  : `<span class="badge badge-secondary">Manual</span>`;
                const newBadge = log.new_emails > 0
                  ? `<span class="badge badge-success">${log.new_emails}</span>`
                  : `<span class="text-muted">0</span>`;
                return `<tr><td>${time}</td><td>${srcBadge}</td><td>${log.emails_fetched}</td><td>${newBadge}</td></tr>`;
              }).join("")}
            </tbody>
          </table>`;
      } else {
        fetchLogsHtml = '<p class="text-muted">No fetch history yet.</p>';
      }

      // Analysis history table
      let analysisLogsHtml = "";
      if (analysisLogs.length > 0) {
        analysisLogsHtml = `
          <table class="fetch-history-table">
            <thead><tr><th>Time</th><th>Source</th><th>Analyzed</th><th>Skipped</th></tr></thead>
            <tbody>
              ${analysisLogs.map((log) => {
                const time = log.created_at ? new Date(log.created_at).toLocaleString() : "";
                const srcBadge = log.source === "scheduler"
                  ? `<span class="badge badge-info">Auto</span>`
                  : `<span class="badge badge-secondary">Manual</span>`;
                const analyzedBadge = log.emails_analyzed > 0
                  ? `<span class="badge badge-success">${log.emails_analyzed}</span>`
                  : `<span class="text-muted">0</span>`;
                const skippedBadge = log.emails_skipped > 0
                  ? `<span class="badge badge-warning">${log.emails_skipped}</span>`
                  : `<span class="text-muted">0</span>`;
                return `<tr><td>${time}</td><td>${srcBadge}</td><td>${analyzedBadge}</td><td>${skippedBadge}</td></tr>`;
              }).join("")}
            </tbody>
          </table>`;
      } else {
        analysisLogsHtml = '<p class="text-muted">No analysis history yet.</p>';
      }

      // VT scan history table
      let vtLogsHtml = "";
      if (vtLogs.length > 0) {
        vtLogsHtml = `
          <table class="fetch-history-table">
            <thead><tr><th>Time</th><th>Source</th><th>Checked</th><th>Skipped</th><th>Errors</th><th>Quota Left</th></tr></thead>
            <tbody>
              ${vtLogs.map((log) => `
                <tr>
                  <td>${log.created_at ? new Date(log.created_at).toLocaleString() : ""}</td>
                  <td><span class="badge ${log.source === "manual" ? "badge-secondary" : "badge-info"}">${log.source}</span></td>
                  <td>${log.checked}</td>
                  <td>${log.skipped}</td>
                  <td>${log.errors}</td>
                  <td>${log.quota_remaining}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>`;
      } else {
        vtLogsHtml = '<p class="text-muted">No VirusTotal scan history yet.</p>';
      }

      // VT results table
      let vtResultsHtml = "";
      if (vtResults.length > 0) {
        vtResultsHtml = `
          <div class="table-scroll">
            <table class="fetch-history-table">
              <thead><tr><th>Checked At</th><th>URL</th><th>Status</th><th>Malicious</th><th>Suspicious</th><th>Harmless</th><th>Undetected</th></tr></thead>
              <tbody>
                ${vtResults.slice(0, 30).map((r) => {
                  let vtReportLink = "";
                  if (r.url && r.status === "success") {
                    try {
                      const urlId = btoa(r.url).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
                      vtReportLink = `<a href="https://www.virustotal.com/gui/url/${urlId}/detection" target="_blank" rel="noopener noreferrer" title="View on VirusTotal" style="margin-left:6px;font-size:0.8rem;opacity:0.7">↗ VT</a>`;
                    } catch (_) {}
                  }
                  return `
                  <tr>
                    <td>${r.last_checked_at ? new Date(r.last_checked_at).toLocaleString() : ""}</td>
                    <td class="vt-url-cell">
                      <a href="${this.escapeHtml(r.url || "#")}" target="_blank" rel="noopener noreferrer">
                        ${this.escapeHtml(r.url || "")}
                      </a>
                      ${vtReportLink}
                    </td>
                     <td>${
                       r.status === "success"
                         ? '<span class="badge badge-success">success</span>'
                         : r.status === "pending_scan"
                           ? '<span class="badge badge-warning">pending</span>'
                           : `<span class="badge badge-danger">${r.status}</span>`
                     }</td>
                    <td>${r.malicious ?? 0}</td>
                    <td>${r.suspicious ?? 0}</td>
                    <td>${r.harmless ?? 0}</td>
                    <td>${r.undetected ?? 0}</td>
                  </tr>
                `}).join("")}
              </tbody>
            </table>
          </div>
          <p class="text-muted" style="margin-top:8px;font-size:0.78rem">Showing latest 30 results</p>`;
      } else {
        vtResultsHtml = '<p class="text-muted">No VirusTotal link results yet.</p>';
      }

      // Translation stats
      const trTotal = trStats.total_runs ?? 0;
      const trOk    = trStats.success_count ?? 0;
      const trFail  = trStats.failure_count ?? 0;
      const lastTr  = trStats.last_translation_at
        ? new Date(trStats.last_translation_at).toLocaleString() : "Never";

      let translationLogsHtml = "";
      if (translationLogs.length > 0) {
        translationLogsHtml = `
          <div class="table-scroll">
            <table class="fetch-history-table">
              <thead>
                <tr>
                  <th>Time</th><th>OK</th><th>Source</th><th>Email</th>
                  <th>Chars</th><th>Chunks</th><th>URLs kept</th><th>Model</th><th>ms</th><th>Error</th>
                </tr>
              </thead>
              <tbody>
                ${translationLogs.map((log) => `
                  <tr>
                    <td>${log.created_at ? new Date(log.created_at).toLocaleString() : ""}</td>
                    <td><span class="badge ${log.success ? "badge-success" : "badge-danger"}">${log.success ? "yes" : "no"}</span></td>
                    <td><span class="badge ${log.source === "email" ? "badge-info" : "badge-secondary"}">${this.escapeHtml(log.source || "")}</span></td>
                    <td>${log.email_id != null ? log.email_id : "—"}</td>
                    <td>${log.source_chars ?? 0}</td>
                    <td>${log.chunk_count ?? 0}</td>
                    <td>${log.urls_preserved ?? 0}</td>
                    <td><small>${this.escapeHtml((log.model || "").substring(0, 24))}</small></td>
                    <td>${log.duration_ms ?? 0}</td>
                    <td class="vt-url-cell"><small>${log.error_message ? this.escapeHtml(String(log.error_message).substring(0, 120)) : "—"}</small></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>`;
      } else {
        translationLogsHtml = '<p class="text-muted">No translation runs yet.</p>';
      }

      document.getElementById("app-content").innerHTML = `
        <div class="fetch-history-page">
          <div class="fetch-history-header">
            <h1>Sync &amp; Analysis Log</h1>
            <div class="header-actions">
              <button class="btn btn-primary btn-sm" onclick="app.fetchEmails()">Fetch Now</button>
              <button class="btn btn-secondary btn-sm" onclick="app.runVTScanNow()">Run VT Scan</button>
            </div>
          </div>

          <div class="fetch-status-cards">
            <div class="status-card"><h3>Total Emails</h3><p class="status-value">${total_emails}</p></div>
            <div class="status-card"><h3>Last Fetch</h3><p class="status-value">${lastSync}</p></div>
            <div class="status-card"><h3>Last Analysis</h3><p class="status-value">${lastAnalysis}</p></div>
            <div class="status-card"><h3>Unanalyzed</h3><p class="status-value ${unanalyzed_count > 0 ? "status-warning" : ""}">${unanalyzed_count}</p></div>
            <div class="status-card"><h3>Auto-Fetch</h3><p class="status-value status-active">Every 5 min</p></div>
            <div class="status-card"><h3>Auto-Analysis</h3><p class="status-value status-active">Every 5 min</p></div>
            <div class="status-card"><h3>VT Used Today</h3><p class="status-value">${vtUsage.used}/${vtUsage.limit}</p></div>
            <div class="status-card"><h3>VT Remaining</h3><p class="status-value ${vtUsage.remaining < 20 ? "status-warning" : "status-active"}">${vtUsage.remaining}</p></div>
            <div class="status-card"><h3>Last Translation</h3><p class="status-value">${lastTr}</p></div>
            <div class="status-card"><h3>Translation Runs</h3><p class="status-value">${trTotal} <small class="text-muted">(${trOk} ok / ${trFail} fail)</small></p></div>
            <div class="status-card"><h3>Translated Chars</h3><p class="status-value">${trStats.total_source_chars_ok ?? 0}</p></div>
            <div class="status-card"><h3>Gemini Chunks</h3><p class="status-value">${trStats.total_chunks_ok ?? 0}</p></div>
          </div>

          <div class="sync-log-sections">
            <div class="fetch-history-list"><h2>Translation (AI) History</h2>${translationLogsHtml}</div>
            <div class="fetch-history-list"><h2>VirusTotal Link Results</h2>${vtResultsHtml}</div>
            <div class="fetch-history-list"><h2>VirusTotal Scan History</h2>${vtLogsHtml}</div>
            <div class="fetch-history-list"><h2>Fetch History</h2>${fetchLogsHtml}</div>
            <div class="fetch-history-list"><h2>Analysis History</h2>${analysisLogsHtml}</div>
          </div>
        </div>
      `;
      this.updateSidebar();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to load sync log"));
      if (error.isAuthError || error.type === "AUTH_ERROR") {
        this.showLoginOverlay();
      }
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Email Management Page
  // ──────────────────────────────────────────────────────────────────

  async renderEmailManagement() {
    if (!authManager.getIsAuthenticated()) {
      this.showLoginOverlay();
      return;
    }

    try {
      this.selectedEmails.clear();
      const response = await api.getEmails(100, 0);
      const emails = response.data.emails || [];
      this.emailManagementData = emails;

      document.getElementById("app-content").innerHTML = `
        <div class="email-management">
          <div class="email-management-header">
            <h1>Email Management</h1>
            <div class="header-actions">
              <button class="btn btn-primary btn-sm" onclick="app.analyzeAllEmails()">Analyze All</button>
              <button class="btn btn-secondary btn-sm" onclick="app.fetchEmails()">Fetch New</button>
            </div>
          </div>

          <div id="bulk-action-bar" class="bulk-action-bar" style="display:none;">
            <div class="bulk-action-info"><span id="selected-count">0</span> email(s) selected</div>
            <div class="bulk-action-buttons">
              <button class="btn btn-primary btn-sm" style="background:#fff;color:var(--primary);border-color:#fff" onclick="app.analyzeSelectedEmails()">Analyze Selected</button>
              <button class="btn btn-sm" style="background:rgba(255,255,255,0.2);color:#fff;border-color:transparent" onclick="app.clearSelection()">Clear</button>
            </div>
          </div>

          <div id="analytics-dashboard" class="analytics-dashboard" style="display:none;"></div>

          <div class="email-list-container">
            ${this.renderEmailList(emails)}
          </div>
        </div>
      `;

      this.updateSidebar();
      this.updateBulkActionBar();
      this.updateAnalyticsDashboard();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to load emails"));
      if (error.isAuthError || error.type === "AUTH_ERROR") {
        this.showLoginOverlay();
      }
    }
  }

  renderEmailList(emails) {
    if (emails.length === 0) {
      return `<div class="empty-state"><p>No emails found.</p><button class="btn btn-primary" onclick="app.fetchEmails()">Fetch Emails</button></div>`;
    }

    const allSelected = emails.length > 0 && emails.every((e) => this.selectedEmails.has(e.id));
    return `
      <div class="table-scroll">
        <table class="email-management-table">
          <thead>
            <tr>
              <th style="width:36px"><input type="checkbox" id="select-all-checkbox" ${allSelected ? "checked" : ""} onchange="app.toggleSelectAll(this.checked)"></th>
              <th>Subject</th>
              <th>Sender</th>
              <th>Date</th>
              <th>Prediction</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${emails.map((email) => `
              <tr class="${this.selectedEmails.has(email.id) ? "selected" : ""}">
                <td><input type="checkbox" class="email-checkbox" value="${email.id}" ${this.selectedEmails.has(email.id) ? "checked" : ""} onchange="app.toggleEmailSelection(${email.id}, this.checked)"></td>
                <td>${email.subject || "(No Subject)"}</td>
                <td>${email.sender || ""}</td>
                <td>${email.received_at ? email.received_at.substring(0, 10) : ""}</td>
                <td>${this.renderPredictionBadge(email.prediction)}</td>
                <td><button class="btn btn-sm btn-secondary" onclick="app.viewEmail(${email.id})">View</button></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  toggleEmailSelection(emailId, isSelected) {
    if (isSelected) this.selectedEmails.add(emailId);
    else this.selectedEmails.delete(emailId);

    const row = document.querySelector(`tr:has(input[value="${emailId}"])`);
    if (row) row.classList.toggle("selected", isSelected);

    this.updateBulkActionBar();
    this.updateAnalyticsDashboard();
  }

  toggleSelectAll(selectAll) {
    if (!this.emailManagementData) return;
    if (selectAll) this.emailManagementData.forEach((e) => this.selectedEmails.add(e.id));
    else this.selectedEmails.clear();

    document.querySelectorAll(".email-checkbox").forEach((cb) => { cb.checked = selectAll; });
    document.querySelectorAll(".email-management-table tbody tr").forEach((row) => {
      row.classList.toggle("selected", selectAll);
    });

    this.updateBulkActionBar();
    this.updateAnalyticsDashboard();
  }

  clearSelection() {
    this.selectedEmails.clear();
    document.querySelectorAll(".email-checkbox").forEach((cb) => { cb.checked = false; });
    document.querySelectorAll("#select-all-checkbox").forEach((cb) => { cb.checked = false; });
    document.querySelectorAll(".email-management-table tbody tr").forEach((row) => {
      row.classList.remove("selected");
    });
    this.updateBulkActionBar();
    this.updateAnalyticsDashboard();
  }

  updateBulkActionBar() {
    const bar = document.getElementById("bulk-action-bar");
    const countEl = document.getElementById("selected-count");
    if (this.selectedEmails.size > 0) {
      if (bar) bar.style.display = "flex";
      if (countEl) countEl.textContent = this.selectedEmails.size;
    } else {
      if (bar) bar.style.display = "none";
    }
  }

  updateAnalyticsDashboard() {
    const dashboard = document.getElementById("analytics-dashboard");
    if (!dashboard || !this.emailManagementData) return;

    if (this.selectedEmails.size === 0) {
      dashboard.style.display = "none";
      return;
    }

    const selectedData = this.emailManagementData.filter((e) => this.selectedEmails.has(e.id));
    const total      = selectedData.length;
    const analyzed   = selectedData.filter((e) => e.prediction).length;
    const phishing   = selectedData.filter((e) => e.prediction && e.prediction.prediction == 1).length;
    const benign     = selectedData.filter((e) => e.prediction && e.prediction.prediction == 0).length;
    const notAnalyzed = total - analyzed;

    const confidences    = selectedData.filter((e) => e.prediction).map((e) => e.prediction.probability);
    const avgConfidence  = confidences.length ? confidences.reduce((a, b) => a + b, 0) / confidences.length : 0;
    const maxConfidence  = confidences.length ? Math.max(...confidences) : 0;
    const minConfidence  = confidences.length ? Math.min(...confidences) : 0;
    const phishingPct    = analyzed > 0 ? (phishing / analyzed) * 100 : 0;

    dashboard.style.display = "block";
    dashboard.innerHTML = `
      <h2>Selection Analytics</h2>
      <div class="analytics-grid">
        <div class="analytics-card"><h3>Total Selected</h3><p class="analytics-value">${total}</p></div>
        <div class="analytics-card"><h3>Phishing</h3><p class="analytics-value phishing">${phishing}</p><p class="analytics-percentage">${analyzed > 0 ? phishingPct.toFixed(1) : 0}%</p></div>
        <div class="analytics-card"><h3>Benign</h3><p class="analytics-value benign">${benign}</p><p class="analytics-percentage">${analyzed > 0 ? ((benign / analyzed) * 100).toFixed(1) : 0}%</p></div>
        <div class="analytics-card"><h3>Not Analyzed</h3><p class="analytics-value">${notAnalyzed}</p></div>
        ${analyzed > 0 ? `
          <div class="analytics-card"><h3>Avg Confidence</h3><p class="analytics-value">${(avgConfidence * 100).toFixed(2)}%</p></div>
          <div class="analytics-card"><h3>Range</h3><p class="analytics-value">${(minConfidence * 100).toFixed(1)}–${(maxConfidence * 100).toFixed(1)}%</p></div>
        ` : `<div class="analytics-card full-width"><p class="text-muted">No analyzed emails selected. Click "Analyze Selected".</p></div>`}
      </div>
      ${analyzed > 0 ? `
        <div class="analytics-visualization">
          <h3>Phishing vs Benign</h3>
          <div class="breakdown-bar">
            <div class="breakdown-segment phishing" style="width:${phishingPct}%"><span>Phishing (${phishing})</span></div>
            <div class="breakdown-segment benign" style="width:${100 - phishingPct}%"><span>Benign (${benign})</span></div>
          </div>
        </div>
      ` : ""}
    `;
  }

  async analyzeAllEmails() {
    if (!this.emailManagementData || this.emailManagementData.length === 0) {
      this.showError("No emails available to analyze");
      return;
    }
    this.selectedEmails.clear();
    this.emailManagementData.forEach((e) => this.selectedEmails.add(e.id));
    document.querySelectorAll(".email-checkbox").forEach((cb) => { cb.checked = true; });
    const selectAll = document.getElementById("select-all-checkbox");
    if (selectAll) selectAll.checked = true;
    document.querySelectorAll(".email-management-table tbody tr").forEach((r) => r.classList.add("selected"));
    this.updateBulkActionBar();
    this.updateAnalyticsDashboard();
    await this.analyzeSelectedEmails();
  }

  async analyzeSelectedEmails() {
    if (this.selectedEmails.size === 0) {
      this.showError("Please select at least one email");
      return;
    }

    const emailIds = Array.from(this.selectedEmails);
    const total = emailIds.length;
    let completed = 0, successful = 0, failed = 0;

    try {
      this.showLoading(`Analyzing emails… (0/${total})`);

      const progressHtml = `
        <div id="bulk-analysis-progress" class="bulk-analysis-progress">
          <div class="progress-bar"><div class="progress-fill" style="width:0%"></div></div>
          <p>Analyzing ${total} email(s)… <span id="progress-text">0/${total}</span></p>
        </div>
      `;
      const contentEl = document.getElementById("app-content");
      if (contentEl) {
        document.getElementById("bulk-analysis-progress")?.remove();
        contentEl.insertAdjacentHTML("afterbegin", progressHtml);
      }

      for (const emailId of emailIds) {
        try {
          await api.analyzeStoredEmail(emailId);
          successful++;
          if (this.emailManagementData) {
            const email = this.emailManagementData.find((e) => e.id === emailId);
            if (email) {
              const emailResponse = await api.getEmail(emailId);
              Object.assign(email, emailResponse.data);
            }
          }
        } catch (error) {
          failed++;
        }

        completed++;
        const pct = (completed / total) * 100;
        document.querySelector(".progress-fill")?.style && (document.querySelector(".progress-fill").style.width = `${pct}%`);
        const progressText = document.getElementById("progress-text");
        if (progressText) progressText.textContent = `${completed}/${total}`;
        this.showLoading(`Analyzing emails… (${completed}/${total})`);
      }

      document.getElementById("bulk-analysis-progress")?.remove();
      if (successful > 0) this.showSuccess(`Successfully analyzed ${successful} email(s)`);
      if (failed > 0)     this.showError(`Failed to analyze ${failed} email(s)`);

      await this.renderEmailManagement();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to analyze emails"));
    } finally {
      this.hideLoading();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Prediction HTML Builder (shared by viewEmail + analyze actions)
  // ──────────────────────────────────────────────────────────────────

  _buildPredictionHtml(pred, details = {}) {
    const classification = pred.classification || (pred.prediction == 1 ? "PHISHING" : "LEGITIMATE");
    const ensembleScore  = pred.ensemble_score || pred.probability;

    let alertClass = "alert-success", alertIcon = "✓", alertTitle = "Legitimate Email";
    if (classification === "PHISHING")  { alertClass = "alert-danger";  alertIcon = "⚠️"; alertTitle = "Phishing Detected!"; }
    if (classification === "SUSPICIOUS"){ alertClass = "alert-warning"; alertIcon = "⚡"; alertTitle = "Suspicious Email"; }

    const inputSrc = pred.input_source || "original";
    const inputSrcLabel =
      inputSrc === "translated_body"
        ? '<span class="badge badge-info">ML on English translation</span>'
        : inputSrc === "manual_paste"
          ? '<span class="badge badge-secondary">ML on pasted text</span>'
          : '<span class="badge badge-secondary">ML on original body</span>';

    let html = `
      <div class="alert ${alertClass}">
        <strong>${alertIcon} ${alertTitle}</strong>
        <p>Classification: <strong>${classification}</strong></p>
        <p>Confidence: ${(ensembleScore * 100).toFixed(2)}%</p>
        <p style="margin-top:8px">${inputSrcLabel}</p>
      </div>
    `;

    if (details.features) {
      const feat = details.features;
      const senderBadge = feat.sender_risk
        ? `<span class="badge badge-${feat.sender_risk === "TRUSTED" ? "success" : "warning"}">${feat.sender_risk}</span>`
        : "";
      html += `
        <div class="analysis-details">
          <h4>Extracted Features</h4>
          <ul class="features-list">
            <li><strong>Links count:</strong> ${feat.links_count || 0}</li>
            <li><strong>Has attachment:</strong> ${feat.has_attachment ? "Yes" : "No"}</li>
            <li><strong>Urgent keywords:</strong> ${feat.urgent_keywords ? "Yes" : "No"}</li>
            <li><strong>Sender domain:</strong> ${feat.sender_domain || "N/A"} ${senderBadge}</li>
          </ul>
        </div>
      `;
    }

    if (details.links && details.links.length > 0) {
      const linksRows = details.links.map((link) => {
        const typeBadge = this.getLinkTypeBadge(link.link_type);
        return `
          <tr>
            <td><code>${link.domain || "N/A"}</code></td>
            <td><span class="badge badge-${typeBadge}">${link.link_type}</span></td>
            <td>${(link.risk_score * 100).toFixed(0)}%</td>
          </tr>
        `;
      }).join("");
      html += `
        <div class="links-analysis">
          <h4>Links Analysis (${details.links.length})</h4>
          <div class="links-table">
            <table><thead><tr><th>Domain</th><th>Type</th><th>Risk</th></tr></thead>
            <tbody>${linksRows}</tbody></table>
          </div>
        </div>
      `;
    }

    if (details.suspicious_segments && details.suspicious_segments.length > 0) {
      const segmentsHtml = details.suspicious_segments.slice(0, 10).map((seg, idx) => {
        const sev = this.getSeverityBadge(seg.severity);
        return `
          <div class="segment-item severity-${seg.severity.toLowerCase()}">
            <div class="segment-header">
              <span class="segment-number">#${idx + 1}</span>
              <span class="segment-severity badge badge-${sev}">${seg.severity}</span>
              <span class="segment-score">${seg.score.toFixed(1)}%</span>
            </div>
            <div class="segment-text">${this.escapeHtml(seg.text)}</div>
            <div class="segment-reasons"><small>${seg.reasons}</small></div>
          </div>
        `;
      }).join("");
      html += `
        <div class="suspicious-segments">
          <h4>Suspicious Text Segments (${details.suspicious_segments.length})</h4>
          <div class="segments-list">${segmentsHtml}</div>
        </div>
      `;
    }

    return html;
  }

  // ──────────────────────────────────────────────────────────────────
  // View Email
  // ──────────────────────────────────────────────────────────────────

  async viewEmail(emailId) {
    // Keep URL in sync so F5 / copy-paste URL reloads the same email
    const emailHash = `email/${emailId}`;
    if (window.location.hash !== `#${emailHash}`) {
      window.history.pushState({ page: emailHash }, "", `#${emailHash}`);
    }
    try {
      this.showLoading();
      const response = await api.getEmail(emailId);
      const email = response.data;

      // Build prediction HTML — route to correct panel based on input_source
      let originalResultHtml = "";
      let translationResultHtml = "";

      if (email.prediction) {
        const pred = email.prediction;
        let detailsData = {};
        let detailsWarning = null;
        try {
          const dr = await api.get(`/predictions/details/${pred.id}`);
          detailsData = dr.data || {};
        } catch (detailsError) {
          // 404 = no detail record yet, silently skip; surface any other failure
          if (detailsError.statusCode !== 404) {
            detailsWarning = detailsError.message || "Unknown error";
          }
        }

        let predHtml = this._buildPredictionHtml(pred, detailsData);
        if (detailsWarning) {
          predHtml += `
            <div class="alert alert-warning" style="margin-top:12px">
              <strong>Warning:</strong> Could not load full analysis details.
              <small style="display:block;margin-top:4px;opacity:0.75">${detailsWarning}</small>
            </div>
          `;
        }

        if (pred.input_source === "translated_body") {
          translationResultHtml = predHtml;
        } else {
          originalResultHtml = predHtml;
        }
      } else {
        originalResultHtml = `
          <div class="alert alert-info">
            <strong>Not analyzed yet.</strong>
            <p style="margin-top:8px"><button class="btn btn-primary btn-sm" onclick="app.analyzeStoredEmail(${email.id})">Analyze Now</button></p>
          </div>
        `;
      }

      // VT results for this email
      let vtResults = [];
      let hasPendingVT = false;
      let vtSectionHtml = "";
      try {
        const vtResponse = await api.getEmailVTResults(emailId, 50, 0);
        vtResults = vtResponse.data?.results || [];
        hasPendingVT = vtResults.some((r) => r.status === "pending_scan");
        if (vtResults.length > 0) {
          vtSectionHtml = this._buildVTTableHtml(vtResults, emailId);
        } else {
          vtSectionHtml = `
            <div class="links-analysis">
              <h4>VirusTotal Link Check</h4>
              <p class="text-muted">No results yet for this email.</p>
              <button class="btn btn-sm btn-primary" onclick="app.runVTScanNowForEmail(${email.id})">Run VT Scan</button>
            </div>
          `;
        }
      } catch (vtError) {
        // 404 = no VT results yet, silently skip; surface any other failure
        if (vtError.statusCode !== 404) {
          vtSectionHtml = `
            <div class="links-analysis">
              <h4>VirusTotal Link Check</h4>
              <div class="alert alert-warning">
                Could not load VT results: ${vtError.message || "Unknown error"}
              </div>
            </div>
          `;
        }
      }

      document.getElementById("app-content").innerHTML = `
        <div class="email-detail">
          <div class="page-header" style="margin-bottom:16px">
            <div>
              <h1 class="page-title" style="font-size:1.1rem">${email.subject || "(No Subject)"}</h1>
              <div class="email-meta" style="margin-top:6px">
                <p><strong>From:</strong> ${email.sender || ""}</p>
                <p><strong>To:</strong> ${email.recipient || ""}</p>
                <p><strong>Date:</strong> ${email.received_at || ""}</p>
              </div>
            </div>
            <div class="page-actions">
              <button class="btn btn-secondary btn-sm" onclick="history.back()">Back</button>
              <button class="btn btn-secondary btn-sm" onclick="app.runVTScanNowForEmail(${email.id})">Refresh VT</button>
            </div>
          </div>

          <div class="email-body">
            <h3>Email Content</h3>
            <div class="dual-panel">
              <!-- LEFT: Original body + original analysis result -->
              <div class="panel-card">
                <div class="panel-card-header">
                  <span class="panel-label">Original</span>
                  <div class="panel-card-actions">
                    <button class="btn btn-sm btn-secondary" onclick="app.translateEmailBodyToEnglish(${email.id})">
                      Translate to English →
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="app.analyzeStoredEmail(${email.id})">
                      Analyze Original
                    </button>
                  </div>
                </div>
                <div class="panel-card-body">
                  <pre>${this.escapeHtml(email.body || "")}</pre>
                </div>
                <div class="panel-analysis-result" id="email-original-result">${originalResultHtml}</div>
              </div>

              <!-- RIGHT: English translation + translation analysis result -->
              <div class="panel-card">
                <div class="panel-card-header">
                  <span class="panel-label panel-label-en">English Translation</span>
                  <div class="panel-card-actions" id="email-translation-actions" style="display:none">
                    <span class="panel-saved-badge" id="email-translation-badge">✓ Saved</span>
                    <span class="panel-meta" id="email-translation-meta"></span>
                    <button class="btn btn-sm btn-secondary" onclick="app.translateEmailBodyToEnglish(${email.id})">Re-translate</button>
                    <button class="btn btn-sm btn-primary" onclick="app.analyzeTranslatedEmail(${email.id})">Analyze Translation</button>
                  </div>
                  <span id="email-translate-status" class="panel-meta" style="display:none"></span>
                </div>
                <div class="panel-card-body">
                  <div id="email-translation-empty" class="panel-empty-state">
                    <div class="panel-empty-icon">🌐</div>
                    <div>
                      <strong>No translation saved</strong><br>
                      <span style="font-size:0.8rem">Click "Translate to English →" to generate and save one.</span>
                    </div>
                  </div>
                  <pre id="email-translation-text" style="display:none"></pre>
                </div>
                <div class="panel-analysis-result" id="email-translation-result">${translationResultHtml}</div>
              </div>
            </div>
          </div>

          ${vtSectionHtml ? `<div class="card" id="email-vt-card" style="margin-top:16px;padding:1rem">${vtSectionHtml}</div>` : ""}
        </div>
      `;
      this.updateSidebar();

      // Auto-load saved translation (non-blocking)
      this._loadSavedTranslation(email.id);

      // Short-poll VT results if any URLs are still being analyzed by VirusTotal
      this._stopVTPoll();
      if (hasPendingVT) this._startVTPoll(email.id);
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to load email"));
      if (error.isAuthError || error.type === "AUTH_ERROR") this.showLoginOverlay();
    } finally {
      this.hideLoading();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // VT helpers: table HTML builder + short-poll
  // ──────────────────────────────────────────────────────────────────

  _buildVTTableHtml(vtResults, emailId) {
    const vtRows = vtResults.map((r) => {
      const statusBadge =
        r.status === "success"
          ? '<span class="badge badge-success">success</span>'
          : r.status === "pending_scan"
            ? '<span class="badge badge-warning">pending</span>'
            : `<span class="badge badge-danger">${r.status}</span>`;

      // Build VirusTotal report link: https://www.virustotal.com/gui/url/<base64url(url)>
      let vtReportLink = "";
      if (r.url && r.status === "success") {
        try {
          const urlId = btoa(r.url).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
          vtReportLink = `<a href="https://www.virustotal.com/gui/url/${urlId}/detection" target="_blank" rel="noopener noreferrer" title="View full report on VirusTotal" style="margin-left:6px;font-size:0.8rem;opacity:0.7">↗ VT</a>`;
        } catch (_) {}
      }

      return `
        <tr>
          <td>${r.last_checked_at ? new Date(r.last_checked_at).toLocaleString() : ""}</td>
          <td class="vt-url-cell">
            <a href="${this.escapeHtml(r.url || "#")}" target="_blank" rel="noopener noreferrer">${this.escapeHtml(r.url || "")}</a>
            ${vtReportLink}
          </td>
          <td>${statusBadge}</td>
          <td>${r.malicious ?? 0}</td>
          <td>${r.suspicious ?? 0}</td>
          <td>${r.harmless ?? 0}</td>
          <td>${r.undetected ?? 0}</td>
        </tr>
      `;
    }).join("");
    const hasPending = vtResults.some((r) => r.status === "pending_scan");
    const pendingNote = hasPending
      ? `<p class="text-muted" style="margin-top:8px;font-size:0.82rem">Pending URLs are queued for analysis — this page refreshes automatically.</p>`
      : "";
    return `
      <div class="links-analysis">
        <h4>VirusTotal Link Check (${vtResults.length})</h4>
        <div class="table-scroll">
          <table class="fetch-history-table">
            <thead><tr><th>Checked At</th><th>URL</th><th>Status</th><th>Malicious</th><th>Suspicious</th><th>Harmless</th><th>Undetected</th></tr></thead>
            <tbody>${vtRows}</tbody>
          </table>
        </div>
        ${pendingNote}
      </div>
    `;
  }

  _startVTPoll(emailId) {
    const MAX_POLLS = 12;  // 1 minute at 5s intervals
    let count = 0;
    this._vtPollTimer = setInterval(async () => {
      count++;
      const cardEl = document.getElementById("email-vt-card");
      if (!cardEl) { this._stopVTPoll(); return; }   // navigated away
      try {
        const resp = await api.getEmailVTResults(emailId, 50, 0);
        const results = resp.data?.results || [];
        cardEl.innerHTML = this._buildVTTableHtml(results, emailId);
        const stillPending = results.some((r) => r.status === "pending_scan");
        if (!stillPending || count >= MAX_POLLS) this._stopVTPoll();
      } catch (_) {
        this._stopVTPoll();
      }
    }, 5000);
  }

  _stopVTPoll() {
    if (this._vtPollTimer) { clearInterval(this._vtPollTimer); this._vtPollTimer = null; }
  }

  async _loadSavedTranslation(emailId) {
    try {
      const resp = await api.getEmailLatestTranslation(emailId);
      const d = resp.data || {};
      if (d.translated_text) {
        this._populateEmailTranslationPanel(d.translated_text, {
          chunk_count: d.chunk_count,
          model: d.model,
          created_at: d.created_at,
          badge: "✓ Saved",
        });
      }
    } catch (_) {
      // 404 = no saved translation — ignore silently
    }
  }

  _populateEmailTranslationPanel(text, meta = {}) {
    const preEl     = document.getElementById("email-translation-text");
    const emptyEl   = document.getElementById("email-translation-empty");
    const actionsEl = document.getElementById("email-translation-actions");
    const metaEl    = document.getElementById("email-translation-meta");
    const badgeEl   = document.getElementById("email-translation-badge");
    const statusEl  = document.getElementById("email-translate-status");
    if (preEl)     { preEl.textContent = text; preEl.style.display = "block"; }
    if (emptyEl)   emptyEl.style.display = "none";
    if (actionsEl) actionsEl.style.display = "flex";
    if (statusEl)  statusEl.style.display = "none";
    if (badgeEl && meta.badge) badgeEl.textContent = meta.badge;
    if (metaEl) {
      const parts = [];
      if (meta.chunk_count != null) parts.push(`${meta.chunk_count} chunk(s)`);
      if (meta.model) parts.push(meta.model);
      if (meta.created_at) parts.push(new Date(meta.created_at).toLocaleDateString());
      metaEl.textContent = parts.join(" · ");
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Analysis Actions
  // ──────────────────────────────────────────────────────────────────

  async handleAnalyze(event, opts = {}) {
    if (event && typeof event.preventDefault === "function") event.preventDefault();
    const emailText = opts.emailText != null
      ? String(opts.emailText).trim()
      : document.getElementById("email_text").value.trim();
    // Which element to write the result into (defaults to "original-analysis-result" or any legacy id)
    const targetId = opts.targetId || "original-analysis-result";

    if (!emailText) { this.showError("Please enter email content"); return; }

    try {
      this.showLoading("Analyzing email…");
      const response = await api.analyzeEmail(emailText);
      const result = response.data;
      const fd = result.formula_details || {};

      let formulaHtml = "";
      if (fd && fd.model) {
        const domainInfo = fd.domain || {};
        const linksInfo  = fd.links  || {};

        const domainBadge = domainInfo.domain_type === "TRUSTED"
          ? '<span class="badge badge-success">TRUSTED</span>'
          : '<span class="badge badge-danger">SUSPICIOUS</span>';

        let linkDetailRows = "";
        if (linksInfo.details && linksInfo.details.length > 0) {
          linkDetailRows = `
            <tr>
              <td colspan="4" style="padding:0">
                <table style="width:100%;margin:0;font-size:0.82em;background:rgba(0,0,0,0.02)">
                  <thead>
                    <tr style="background:rgba(0,0,0,0.05)">
                      <th style="padding:4px 8px">URL / Domain</th>
                      <th style="padding:4px 8px">Type</th>
                      <th style="padding:4px 8px">Risk</th>
                      <th style="padding:4px 8px">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${linksInfo.details.map((l) => `
                      <tr>
                        <td style="padding:4px 8px;word-break:break-all">${l.url}</td>
                        <td style="padding:4px 8px"><span class="badge ${l.type === "TRUSTED" ? "badge-success" : l.type === "NORMAL" ? "badge-secondary" : "badge-danger"}">${l.type}</span></td>
                        <td style="padding:4px 8px">${l.risk}</td>
                        <td style="padding:4px 8px">${l.reason}</td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </td>
            </tr>
          `;
        }

        formulaHtml = `
          <div class="formula-breakdown">
            <h3>Ensemble Formula Details</h3>
            <table class="formula-table">
              <thead>
                <tr><th>Component</th><th>Raw Score</th><th>Weight</th><th>Contribution</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Model Probability</strong></td>
                  <td>${(fd.model.raw_score * 100).toFixed(2)}%</td>
                  <td>${(fd.model.weight * 100).toFixed(0)}%</td>
                  <td><strong>${(fd.model.contribution * 100).toFixed(4)}%</strong></td>
                </tr>
                <tr>
                  <td><strong>Urgent Keywords</strong></td>
                  <td>${fd.urgent_keywords.raw_score}</td>
                  <td>${(fd.urgent_keywords.weight * 100).toFixed(0)}%</td>
                  <td><strong>${(fd.urgent_keywords.contribution * 100).toFixed(4)}%</strong></td>
                </tr>
                <tr>
                  <td><strong>Links Risk</strong> <small>(${linksInfo.count || 0} links)</small></td>
                  <td>${(linksInfo.raw_score * 100).toFixed(2)}%</td>
                  <td>${(linksInfo.weight * 100).toFixed(1)}%</td>
                  <td><strong>${(linksInfo.contribution * 100).toFixed(4)}%</strong></td>
                </tr>
                ${linkDetailRows}
                <tr>
                  <td><strong>Domain Risk</strong><br><small>${domainInfo.domain_name || "unknown"} ${domainBadge}</small><br><small>${domainInfo.reason || ""}</small></td>
                  <td>${(domainInfo.raw_score * 100).toFixed(2)}%</td>
                  <td>${(domainInfo.weight * 100).toFixed(1)}%</td>
                  <td><strong>${(domainInfo.contribution * 100).toFixed(4)}%</strong></td>
                </tr>
              </tbody>
              <tfoot>
                <tr style="background:var(--bg);font-weight:bold">
                  <td colspan="3">Ensemble Score</td>
                  <td style="font-size:1.05em">${(result.ensemble_score * 100).toFixed(4)}%</td>
                </tr>
              </tfoot>
            </table>
            <div class="formula-text"><strong>Formula:</strong> ${fd.formula_text || ""}</div>
          </div>
        `;
      }

      const alertClass = result.is_phishing ? "alert-danger" : result.is_suspicious ? "alert-warning" : "alert-success";
      const alertTitle = result.is_phishing ? "⚠️ Phishing Detected!" : result.is_suspicious ? "⚡ Suspicious Email" : "✓ Legitimate Email";

      const targetEl = document.getElementById(targetId) || document.getElementById("original-analysis-result");
      if (targetEl) targetEl.innerHTML = `
        <div class="panel-analysis-result-inner">
          <div class="alert ${alertClass}" style="margin:0 0 12px">
            <strong>${alertTitle}</strong>
            <p>Classification: <strong>${result.classification}</strong></p>
            <p>Model Probability: ${(result.probability * 100).toFixed(2)}%</p>
            <p>Ensemble Score: ${(result.ensemble_score * 100).toFixed(2)}%</p>
            <p>Threshold: ${(result.threshold * 100).toFixed(2)}%</p>
          </div>
          ${formulaHtml}
        </div>
      `;
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to analyze email"));
    } finally {
      this.hideLoading();
    }
  }

  async analyzeStoredEmail(emailId) {
    const resultEl = document.getElementById("email-original-result");
    if (resultEl) resultEl.innerHTML = '<div class="alert alert-info"><strong>Analyzing…</strong></div>';
    try {
      const res = await api.analyzeStoredEmail(emailId);
      const pred = res.data?.prediction || res.data;
      let details = {};
      if (pred?.id) {
        try {
          const dr = await api.get(`/predictions/details/${pred.id}`);
          details = dr.data || {};
        } catch (_) {}
      }
      if (resultEl) resultEl.innerHTML = this._buildPredictionHtml(pred, details);
      this.showSuccess("Email analyzed successfully");
    } catch (error) {
      if (resultEl) resultEl.innerHTML = "";
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to analyze email"));
    }
  }

  async analyzeTranslatedEmail(emailId) {
    const pre  = document.getElementById("email-translation-text");
    const text = pre && pre.textContent ? pre.textContent.trim() : "";
    if (!text || text === "(Empty)") {
      this.showError("No translation yet — click \"Translate to English (AI)\" first.");
      return;
    }
    const resultEl = document.getElementById("email-translation-result");
    if (resultEl) resultEl.innerHTML = '<div class="alert alert-info"><strong>Analyzing translation…</strong></div>';
    try {
      const res = await api.analyzeStoredEmailTranslated(emailId, text);
      const pred = res.data?.prediction || res.data;
      let details = {};
      if (pred?.id) {
        try {
          const dr = await api.get(`/predictions/details/${pred.id}`);
          details = dr.data || {};
        } catch (_) {}
      }
      if (resultEl) resultEl.innerHTML = this._buildPredictionHtml(pred, details);
      this.showSuccess("Saved analysis result from English translation.");
    } catch (error) {
      if (resultEl) resultEl.innerHTML = "";
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to analyze translated text"));
    }
  }

  async analyzeTranslatedPasteWithML() {
    const pre  = document.getElementById("analyze-translation-text");
    const text = pre && pre.textContent ? pre.textContent.trim() : "";
    if (!text || text === "(Empty)") {
      this.showError("No translation yet — click \"Translate to English →\" first.");
      return;
    }
    await this.handleAnalyze({ preventDefault: () => {} }, { emailText: text, targetId: "translation-analysis-result" });
  }

  async translateEmailBodyToEnglish(emailId) {
    const statusEl = document.getElementById("email-translate-status");
    if (statusEl) { statusEl.textContent = "Translating…"; statusEl.style.display = "inline"; }
    try {
      this.showLoading("Translating to English…");
      const response = await api.translateEmailBodyToEnglish(emailId);
      const d = response.data || {};
      this._populateEmailTranslationPanel(d.translated_text || "", {
        chunk_count: d.chunk_count,
        model: d.model,
        badge: "✓ Saved",
      });
      if (statusEl) statusEl.style.display = "none";
      this.showSuccess("Translation saved");
    } catch (error) {
      if (statusEl) { statusEl.textContent = ""; statusEl.style.display = "none"; }
      this.showError(this.getUserFriendlyErrorMessage(error, "Translation failed"));
    } finally {
      this.hideLoading();
    }
  }

  async translateAnalyzeTextToEnglish() {
    const ta       = document.getElementById("email_text");
    const statusEl = document.getElementById("analyze-translate-status");
    const actionsEl = document.getElementById("analyze-translation-actions");
    const metaEl   = document.getElementById("analyze-translation-meta");
    const preEl    = document.getElementById("analyze-translation-text");
    const emptyEl  = document.getElementById("analyze-translation-empty");
    const raw = ta ? ta.value.trim() : "";
    if (!raw) { this.showError("Please enter some text to translate"); return; }
    if (statusEl) statusEl.textContent = "Translating…";
    try {
      this.showLoading("Translating to English…");
      const response = await api.translateTextToEnglish(raw);
      const d = response.data || {};
      const translated = d.translated_text || "";
      // Show translated text in right panel
      if (preEl)    { preEl.textContent = translated || "(Empty)"; preEl.style.display = "block"; }
      if (emptyEl)  emptyEl.style.display = "none";
      if (actionsEl) actionsEl.style.display = "flex";
      if (metaEl) {
        const parts = [];
        if (d.chunk_count != null) parts.push(`${d.chunk_count} chunk(s)`);
        if (d.model) parts.push(d.model);
        metaEl.textContent = parts.join(" · ");
      }
      if (statusEl) statusEl.textContent = "Translation ready.";
      this.showSuccess("Translation completed");
    } catch (error) {
      if (statusEl) statusEl.textContent = "";
      this.showError(this.getUserFriendlyErrorMessage(error, "Translation failed"));
    } finally {
      this.hideLoading();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // VirusTotal Actions
  // ──────────────────────────────────────────────────────────────────

  async runVTScanNow() {
    try {
      this.showLoading("Running VirusTotal scan…");
      const response = await api.runVTScanNow();
      const d = response.data || {};
      this.showSuccess(`VT scan done: checked ${d.checked || 0}, skipped ${d.skipped || 0}, errors ${d.errors || 0}, remaining ${d.quota_remaining || 0}`);
      if (this.currentPage === "fetch-history") await this.renderFetchHistory();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to run VirusTotal scan"));
    } finally {
      this.hideLoading();
    }
  }

  async runVTScanNowForEmail(emailId) {
    try {
      this.showLoading("Running VirusTotal scan for this email…");
      this._stopVTPoll();
      const response = await api.runVTScanNowForEmail(emailId);
      const d = response.data || {};
      this.showSuccess(`VT scan: checked ${d.checked || 0}, skipped ${d.skipped || 0}, errors ${d.errors || 0}, remaining ${d.quota_remaining || 0}`);
      await this.viewEmail(emailId);
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to run VT scan"));
    } finally {
      this.hideLoading();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Fetch Emails
  // ──────────────────────────────────────────────────────────────────

  async fetchEmails() {
    try {
      this.showLoading("Fetching emails…");
      const response = await api.fetchEmails();
      const newCount   = response.data?.new_count || 0;
      const totalCount = response.data?.count || 0;
      this.showSuccess(
        newCount > 0
          ? `Fetched ${totalCount} emails (${newCount} new)`
          : `Fetched ${totalCount} emails (no new emails)`
      );
      if (this.lastKnownEmailCount !== null) this.lastKnownEmailCount += newCount;
      if (this.currentPage === "fetch-history") await this.renderFetchHistory();
      else if (this.currentPage === "stats") await this.renderStats();
      else await this.renderEmails();
    } catch (error) {
      this.showError(this.getUserFriendlyErrorMessage(error, "Failed to fetch emails"));
    } finally {
      this.hideLoading();
    }
  }

  // ──────────────────────────────────────────────────────────────────
  // Sign Out
  // ──────────────────────────────────────────────────────────────────

  async disconnectAccount() {
    try {
      this.showLoading("Signing out…");
      await authManager.disconnect();
      this.hideLoading();
      this.showLoginOverlay();
    } catch (error) {
      this.hideLoading();
      this.showLoginOverlay(); // Clear UI regardless
    }
  }

  // Keep old name for any lingering references
  async disconnectGmail() { return this.disconnectAccount(); }

  // ──────────────────────────────────────────────────────────────────
  // UI Helpers
  // ──────────────────────────────────────────────────────────────────

  showLoading(message = "Loading…") {
    const el   = document.getElementById("loading");
    const text = document.getElementById("loading-text");
    if (el) el.style.display = "flex";
    if (text) text.textContent = message;
  }

  hideLoading() {
    const el = document.getElementById("loading");
    if (el) el.style.display = "none";
  }

  showError(message)   { this.showMessage(message, "error"); }
  showSuccess(message) { this.showMessage(message, "success"); }

  showMessage(message, type) {
    const container = document.getElementById("messages");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `flash flash-${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }

  getUserFriendlyErrorMessage(error, defaultMessage = "An error occurred") {
    if (error && error.type) {
      switch (error.type) {
        case "AUTH_ERROR":    return "Your session has expired. Please sign in again.";
        case "NETWORK_ERROR": return "Unable to connect to the server. Please check your internet connection.";
        case "API_ERROR":     return error.message || `${defaultMessage}. Please try again.`;
        default:              return error.message || defaultMessage;
      }
    }
    if (error && error.message) {
      if (error.message.toLowerCase().includes("session") ||
          error.message.toLowerCase().includes("authenticated") ||
          error.message.toLowerCase().includes("unauthorized")) {
        return "Your session has expired. Please sign in again.";
      }
      return error.message;
    }
    return defaultMessage;
  }

  // ──────────────────────────────────────────────────────────────────
  // Render Helpers
  // ──────────────────────────────────────────────────────────────────

  getLinkTypeBadge(type) {
    return { TRUSTED: "success", NORMAL: "info", SHORTENER: "warning", IP_BASED: "danger", SUSPICIOUS: "danger" }[type] || "secondary";
  }

  getSeverityBadge(severity) {
    return { HIGH: "danger", MEDIUM: "warning", LOW: "info" }[severity] || "secondary";
  }

  renderInputSourceLabel(inputSource) {
    const src = inputSource || "original";
    if (src === "translated_body") return '<span class="badge badge-info">EN translate</span>';
    if (src === "manual_paste")    return '<span class="badge badge-secondary">Paste</span>';
    return '<span class="badge badge-secondary">Original</span>';
  }

  renderPredictionBadge(prediction, vtSummary) {
    if (!prediction) return '<span class="badge badge-secondary">Not Analyzed</span>';

    const classification = prediction.classification || (prediction.prediction == 1 ? "PHISHING" : "LEGITIMATE");
    const score = prediction.ensemble_score != null ? prediction.ensemble_score : prediction.probability;
    const badgeClass = classification === "PHISHING" ? "badge-danger" : classification === "SUSPICIOUS" ? "badge-warning" : "badge-success";

    const originalBadge = `<span class="badge ${badgeClass}">${classification} ${(score * 100).toFixed(1)}%</span>`;

    // Compute VT-enhanced score only when VT data exists
    if (vtSummary && vtSummary.total_checked > 0) {
      const vtBoost = Math.min(0.30, (vtSummary.total_malicious * 0.15) + (vtSummary.total_suspicious * 0.05));
      const vtScore = Math.min(1.0, score + vtBoost);
      // Determine badge class for VT score (use phishing threshold ~0.5)
      const vtClass = vtScore >= 0.7 ? "badge-danger" : vtScore >= 0.4 ? "badge-warning" : "badge-success";
      const pendingNote = vtSummary.has_pending ? ' <span class="badge badge-warning" title="Some links still pending VT scan">~</span>' : "";
      const vtBadge = `<span class="badge ${vtClass}" title="+VirusTotal boost">+VT ${(vtScore * 100).toFixed(1)}%</span>${pendingNote}`;
      return `${originalBadge} ${vtBadge}`;
    }

    return originalBadge;
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// ── Bootstrap ──────────────────────────────────────────────────────
let app;
document.addEventListener("DOMContentLoaded", () => {
  app = new App();
  window.app = app;
});
