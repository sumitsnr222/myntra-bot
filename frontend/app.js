
let currentUser = localStorage.getItem('owner');
let currentRole = localStorage.getItem('role');

if (currentUser) {
    document.getElementById('authOverlay').style.display = 'none';
    applyRoleLimits();
}

function applyRoleLimits() {
    if (currentRole !== 'admin') {
        if(document.getElementById('navLogs')) document.getElementById('navLogs').style.display = 'none';
        if(document.getElementById('navSettings')) document.getElementById('navSettings').style.display = 'none';
        if(document.getElementById('quickLogs')) document.getElementById('quickLogs').style.display = 'none';
    }
}

async function authAction(action) {
    const email = document.getElementById('authEmail').value;
    const pwd = document.getElementById('authPassword').value;
    if(!email || !pwd) return;
    
    try {
        const r = await fetch(`/api/auth/${action}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email, password: pwd})
        });
        const data = await r.json();
        if(data.success) {
            localStorage.setItem('owner', email);
            localStorage.setItem('role', data.role);
            currentUser = email;
            currentRole = data.role;
            document.getElementById('authOverlay').style.display = 'none';
            applyRoleLimits();
            refreshAccounts();
        } else {
            document.getElementById('authError').innerText = data.message;
        }
    } catch(e) {}
}

function logout() {
    localStorage.clear();
    location.reload();
}
/**
 * Myntra Suite — Frontend Logic v3
 * - Myntra-exact login modal with 4-digit OTP
 * - WebSocket live task updates
 * - Auto-focus OTP boxes
 */

const API = "";  // same origin
let ws = null;
let wsReconnectTimer = null;
let currentPhone = "";

// ═══════════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
    updateClock();
    setInterval(updateClock, 30000);
    refreshStats();
    loadBrowserInfo();
    connectWebSocket();
    setupOtpBoxes();

    // Settings page URL
    const apiUrl = document.getElementById("apiUrl");
    if (apiUrl) apiUrl.textContent = window.location.origin;
});

function updateClock() {
    const el = document.getElementById("statusTime");
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
    }
}

// ═══════════════════════════════════════════════════════════════════
//  TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════
function switchTab(tabName) {
    document.querySelectorAll(".tab-page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

    const page = document.getElementById(`page-${tabName}`);
    const nav = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (page) page.classList.add("active");
    if (nav) nav.classList.add("active");

    // Lazy load data
    if (tabName === "accounts") loadAccounts();
    if (tabName === "logs") loadLogs();
    if (tabName === "settings") loadBrowserInfo();
}

// ═══════════════════════════════════════════════════════════════════
//  API HELPERS
// ═══════════════════════════════════════════════════════════════════
async function apiFetch(url, opts = {}) {
    try {
        const resp = await fetch(API + url, {
            headers: { "Content-Type": "application/json", ...opts.headers },
            ...opts,
        });
        return await resp.json();
    } catch (e) {
        console.error("API error:", e);
        return null;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  STATS
// ═══════════════════════════════════════════════════════════════════
async function refreshStats() {
    const data = await apiFetch("/api/stats");
    if (!data) return;
    animateNumber("statAccounts", data.total_accounts || 0);
    animateNumber("statActive", data.active_sessions || 0);
    animateNumber("statTasks", data.tasks_run || 0);
    animateNumber("statSuccess", data.actions_ok || 0);
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const current = parseInt(el.textContent) || 0;
    if (current === target) return;
    const step = target > current ? 1 : -1;
    const diff = Math.abs(target - current);
    const delay = Math.max(20, Math.min(100, 500 / diff));
    let val = current;
    const timer = setInterval(() => {
        val += step;
        el.textContent = val;
        if (val === target) clearInterval(timer);
    }, delay);
}

// ═══════════════════════════════════════════════════════════════════
//  ACCOUNTS
// ═══════════════════════════════════════════════════════════════════
async function loadAccounts() {
    const data = await apiFetch("/api/accounts");
    const list = document.getElementById("accountsList");
    if (!data || !data.accounts.length) {
        list.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div><p>No accounts yet</p><span>Add your first Myntra account above</span></div>`;
        return;
    }
    list.innerHTML = data.accounts.map(acc => `
        <div class="account-card" onclick="viewAccount('${acc.phone}')">
            <div class="account-avatar">${acc.phone.slice(-2)}</div>
            <div class="account-info">
                <div class="account-phone">+91 ${acc.phone}</div>
                <div class="account-meta">${acc.manual ? "Cookie login" : "OTP login"} • ${timeAgo(acc.added_at)}</div>
            </div>
            <span class="account-status ${acc.has_cookies ? 'active' : 'expired'}">${acc.has_cookies ? 'Active' : 'No Session'}</span>
            <button class="account-delete" onclick="event.stopPropagation(); deleteAccount('${acc.phone}')" title="Delete">🗑</button>
        </div>
    `).join("");
}

async function viewAccount(phone) {
    const data = await apiFetch(`/api/accounts/${phone}`);
    if (!data) return;
    const body = document.getElementById("accountModalBody");
    body.innerHTML = `
        <div class="detail-row"><span class="detail-label">Phone</span><span class="detail-value">+91 ${data.phone}</span></div>
        <div class="detail-row"><span class="detail-label">Cookies</span><span class="detail-value">${data.cookie_count} keys</span></div>
        <div class="detail-row"><span class="detail-label">Keys</span><span class="detail-value">${data.cookie_keys?.join(", ") || "—"}</span></div>
        <div class="detail-row"><span class="detail-label">Type</span><span class="detail-value">${data.manual ? "Manual Cookie" : "OTP Login"}</span></div>
        ${data.cookie_string ? `<div class="cookie-box">${escapeHtml(data.cookie_string)}</div><button class="copy-btn" onclick="copyText(\`${escapeHtml(data.cookie_string)}\`)">📋 Copy Cookies</button>` : ""}
    `;
    openModal("accountModal");
}

async function deleteAccount(phone) {
    if (!confirm(`Delete account +91 ${phone}?`)) return;
    const data = await apiFetch(`/api/accounts/${phone}`, { method: "DELETE" });
    if (data?.success) {
        showToast("Account deleted", "success");
        loadAccounts();
        refreshStats();
    } else {
        showToast("Delete failed", "error");
    }
}

// ═══════════════════════════════════════════════════════════════════
//  MYNTRA LOGIN MODAL
// ═══════════════════════════════════════════════════════════════════
function openLoginModal() {
    // Reset to step 1
    document.getElementById("loginStep1").style.display = "block";
    document.getElementById("loginStep2").style.display = "none";
    document.getElementById("loginStep3").style.display = "none";
    document.getElementById("loginPhone").value = "";
    document.getElementById("loginConsent").checked = true;
    document.getElementById("sendOtpBtn").disabled = false;
    document.getElementById("sendOtpBtn").textContent = "CONTINUE";
    clearOtpBoxes();
    openModal("loginModal");
    setTimeout(() => document.getElementById("loginPhone").focus(), 300);
}

function backToPhone() {
    document.getElementById("loginStep1").style.display = "block";
    document.getElementById("loginStep2").style.display = "none";
    document.getElementById("loginStep3").style.display = "none";
    clearOtpBoxes();
}

async function sendOtp() {
    const phone = document.getElementById("loginPhone").value.trim().replace(/\D/g, "");
    const consent = document.getElementById("loginConsent").checked;
    const btn = document.getElementById("sendOtpBtn");

    if (!phone || phone.length !== 10) {
        showToast("Enter a valid 10-digit mobile number", "error");
        return;
    }
    if (!consent) {
        showToast("Please accept Terms & Conditions", "warning");
        return;
    }

    currentPhone = phone;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>';

    const data = await apiFetch("/api/accounts/login", {
        method: "POST",
        body: JSON.stringify({ phone: phone, owner: currentUser }),
    });

    btn.disabled = false;
    btn.textContent = "CONTINUE";

    if (data?.success) {
        showToast("OTP sent! Check your phone 📱", "success");
        // Switch to OTP step
        document.getElementById("loginStep1").style.display = "none";
        document.getElementById("loginStep2").style.display = "block";
        document.getElementById("otpPhone").textContent = `+91 ${phone}`;
        clearOtpBoxes();
        // Focus first OTP box
        setTimeout(() => {
            const firstBox = document.querySelector(".myntra-otp-box[data-idx='0']");
            if (firstBox) firstBox.focus();
        }, 200);
    } else {
        showToast(data?.message || "Failed to send OTP", "error");
    }
}

async function verifyOtp() {
    const boxes = document.querySelectorAll(".myntra-otp-box");
    const otp = Array.from(boxes).map(b => b.value).join("");
    const btn = document.getElementById("verifyOtpBtn");

    if (otp.length !== 4) {
        showToast("Enter all 4 digits", "error");
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>';

    const data = await apiFetch("/api/accounts/verify", {
        method: "POST",
        body: JSON.stringify({ phone: currentPhone, otp }),
    });

    btn.disabled = false;
    btn.textContent = "VERIFY";

    if (data?.success) {
        showToast("Login successful! 🎉", "success");
        document.getElementById("loginStep2").style.display = "none";
        document.getElementById("loginStep3").style.display = "block";
        document.getElementById("loginSuccessMsg").textContent =
            `+91 ${currentPhone} added with ${data.cookies_count || 0} cookies.`;
        refreshStats();
        loadAccounts();
    } else {
        showToast(data?.message || "Verification failed", "error");
        clearOtpBoxes();
    }
}

// ── OTP Box Auto-Focus (4 boxes) ────────────────────────────────
function setupOtpBoxes() {
    document.querySelectorAll(".myntra-otp-box").forEach((box) => {
        box.addEventListener("input", (e) => {
            const val = e.target.value.replace(/\D/g, "");
            e.target.value = val;

            if (val) {
                e.target.classList.add("filled");
                const idx = parseInt(e.target.dataset.idx);
                const next = document.querySelector(`.myntra-otp-box[data-idx='${idx + 1}']`);
                if (next) next.focus();
                // Auto-verify when all 4 filled
                if (idx === 3) {
                    setTimeout(() => verifyOtp(), 300);
                }
            } else {
                e.target.classList.remove("filled");
            }
        });

        box.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && !e.target.value) {
                const idx = parseInt(e.target.dataset.idx);
                const prev = document.querySelector(`.myntra-otp-box[data-idx='${idx - 1}']`);
                if (prev) {
                    prev.value = "";
                    prev.classList.remove("filled");
                    prev.focus();
                }
            }
        });

        // Handle paste
        box.addEventListener("paste", (e) => {
            e.preventDefault();
            const paste = (e.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "");
            if (paste.length >= 4) {
                document.querySelectorAll(".myntra-otp-box").forEach((b, i) => {
                    if (paste[i]) {
                        b.value = paste[i];
                        b.classList.add("filled");
                    }
                });
                setTimeout(() => verifyOtp(), 300);
            }
        });
    });
}

function clearOtpBoxes() {
    document.querySelectorAll(".myntra-otp-box").forEach(b => {
        b.value = "";
        b.classList.remove("filled");
    });
}

// ═══════════════════════════════════════════════════════════════════
//  COOKIE MODAL
// ═══════════════════════════════════════════════════════════════════
function openCookieModal() {
    document.getElementById("cookiePhone").value = "";
    document.getElementById("cookieString").value = "";
    openModal("cookieModal");
}

async function saveCookies() {
    const phone = document.getElementById("cookiePhone").value.trim().replace(/\D/g, "");
    const cookieStr = document.getElementById("cookieString").value.trim();

    if (!phone || phone.length !== 10) {
        showToast("Enter a valid 10-digit number", "error");
        return;
    }
    if (!cookieStr) {
        showToast("Paste your cookie string", "error");
        return;
    }

    const data = await apiFetch("/api/accounts/setcookie", {
        method: "POST",
        body: JSON.stringify({ phone, cookie_string: cookieStr }),
    });

    if (data?.success) {
        showToast(`Cookies saved (${data.keys?.length || 0} keys)`, "success");
        closeModal("cookieModal");
        loadAccounts();
        refreshStats();
    } else {
        showToast(data?.message || "Failed to save cookies", "error");
    }
}

// ═══════════════════════════════════════════════════════════════════
//  TASKS
// ═══════════════════════════════════════════════════════════════════
let selectedMode = "like";

function selectMode(el) {
    document.querySelectorAll(".mode-card").forEach(c => c.classList.remove("active"));
    el.classList.add("active");
    selectedMode = el.dataset.mode;
}

let parseTimer = null;
let extractedProductIds = [];
async function parseTaskUrl() {
    const url = document.getElementById("taskUrl").value.trim();
    if (!url) {
        document.getElementById("taskPostId").value = "";
        document.getElementById("taskAuthorId").value = "";
        document.getElementById("taskProductId").value = "";
        extractedProductIds = [];
        document.getElementById("extractStatus").textContent = "Paste a Myntra Studio URL — IDs will auto-fill ⚡";
        document.getElementById("extractStatus").style.color = "";
        return;
    }
    // Debounce 800ms
    if (parseTimer) clearTimeout(parseTimer);
    parseTimer = setTimeout(async () => {
        document.getElementById("extractStatus").textContent = "⏳ Extracting IDs from URL...";
        document.getElementById("extractStatus").style.color = "#ff9100";
        const data = await apiFetch("/api/tasks/extract", {
            method: "POST",
            body: JSON.stringify({ url }),
        });
        if (data?.success) {
            if (data.post_id) document.getElementById("taskPostId").value = data.post_id;
            if (data.author_id) document.getElementById("taskAuthorId").value = data.author_id;
            if (data.product_id) document.getElementById("taskProductId").value = data.product_id;
            extractedProductIds = data.product_ids || [];
            
            // Auto-select author mode if it's an author profile
            if (data.is_author_profile) {
                document.getElementById("btnAuthorAll").click();
                document.getElementById("taskPostId").value = `All Posts (${extractedProductIds.length} found)`;
                document.getElementById("taskProductId").value = `${extractedProductIds.length} posts with products`;
            }
            
            const found = [
                data.post_id && "Post",
                data.author_id && "Author",
                !data.is_author_profile && data.product_id && `Product (${extractedProductIds.length || 1})`,
                data.is_author_profile && `🌟 ${extractedProductIds.length} Posts Found`
            ].filter(Boolean);
            document.getElementById("extractStatus").textContent = found.length ? `✅ ${found.join(", ")}` : "⚠️ Could not extract IDs. Make sure you have a logged-in account first!";
            document.getElementById("extractStatus").style.color = found.length ? "#00c853" : "#ff3f6c";
        } else {
            document.getElementById("extractStatus").textContent = "❌ Failed to extract";
            document.getElementById("extractStatus").style.color = "#ff3f6c";
        }
    }, 800);
}

async function runTask() {
    const btn = document.getElementById("runTaskBtn");
    const authorId = document.getElementById("taskAuthorId").value.trim();
    const postId = document.getElementById("taskPostId").value.trim();
    const productId = document.getElementById("taskProductId").value.trim();
    const url = document.getElementById("taskUrl").value.trim();

    if (selectedMode === "author_all") {
        // For author mode, we only need the URL and extracted posts
        if (!url || extractedProductIds.length === 0) {
            showToast("Paste an Influencer Profile URL and wait for extraction!", "error");
            return;
        }
    } else if (!postId && !url) {
        showToast("Paste a Myntra Studio URL first!", "error");
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running...';

    const data = await apiFetch("/api/tasks/run", {
        method: "POST",
        body: JSON.stringify({
            mode: selectedMode,
            author_id: authorId || null,
            post_id: postId || "",
            product_id: productId || null,
            product_ids: extractedProductIds.length ? extractedProductIds : null,
        }),
    });

    btn.disabled = false;
    btn.innerHTML = '<span class="run-btn-icon">🚀</span><span>Run on All Accounts</span>';

    if (data?.success) {
        showToast(data.message, "success");
        
        let headerHtml = `<div class="progress-header"><span class="progress-title">⏳ Starting...</span></div>`;
        if (selectedMode === "author_all") {
             headerHtml = `
                <div class="author-tracker">
                    <div class="author-tracker-title">✨ Author Posts Live Tracker</div>
                    <div class="author-tracker-stats" id="authorTrackerStats">Fetching posts...</div>
                </div>
            `;
        }
        
        document.getElementById("taskProgress").innerHTML = `
            ${headerHtml}
            <div class="progress-bar-container"><div class="progress-bar" id="progressBar"></div></div>
            <div id="progressItems"></div>
        `;
    } else {
        showToast(data?.message || data?.detail || "Failed to start task", "error");
    }
}

// ═══════════════════════════════════════════════════════════════════
//  LOGS
// ═══════════════════════════════════════════════════════════════════
async function loadLogs() {
    const data = await apiFetch("/api/logs");
    const container = document.getElementById("logsContainer");
    if (!data || !data.logs?.length) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">📜</div><p>No logs yet</p></div>`;
        return;
    }
    container.innerHTML = data.logs.map(line => {
        const cls = line.includes("✅") || line.includes("True") ? "success" : line.includes("❌") || line.includes("False") ? "fail" : "";
        return `<div class="log-line ${cls}">${escapeHtml(line)}</div>`;
    }).join("");
}

// ═══════════════════════════════════════════════════════════════════
//  BROWSER INFO
// ═══════════════════════════════════════════════════════════════════
async function loadBrowserInfo() {
    const data = await apiFetch("/api/browser-info");
    const label = document.getElementById("engineLabel");
    const badge = document.getElementById("engineBadge");
    if (data?.engine) {
        label.textContent = data.engine;
        badge.className = "setting-badge active";
        badge.textContent = "Active";
    } else {
        label.textContent = "Not connected";
        badge.className = "setting-badge error";
        badge.textContent = "Error";
    }
}

// ═══════════════════════════════════════════════════════════════════
//  WEBSOCKET
// ═══════════════════════════════════════════════════════════════════
function connectWebSocket() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
        const el = document.getElementById("wsStatus");
        const badge = document.getElementById("wsBadge");
        if (el) el.textContent = "Connected";
        if (badge) { badge.textContent = "● Live"; badge.className = "setting-badge active"; }
    };

    ws.onclose = () => {
        const el = document.getElementById("wsStatus");
        const badge = document.getElementById("wsBadge");
        if (el) el.textContent = "Disconnected";
        if (badge) { badge.textContent = "● Offline"; badge.className = "setting-badge error"; }
        wsReconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            handleWsMessage(data);
        } catch (e) {}
    };
}

function handleWsMessage(data) {
    if (data.type === "task_start") {
        addActivity("info", `Task <strong>${data.label}</strong> started on ${data.total} accounts`);
    }
    else if (data.type === "task_progress") {
        if (data.info) {
             const items = document.getElementById("progressItems");
             if (items) {
                 items.innerHTML += `<div class="progress-item info">✨ ${data.message}</div>`;
                 items.scrollTop = items.scrollHeight;
             }
             const authorStats = document.getElementById("authorTrackerStats");
             if (authorStats && data.message.includes("Processing Post")) {
                 authorStats.innerHTML = `<span class="badge info">Loading...</span> ${data.message}`;
             } else if (authorStats) {
                 authorStats.innerHTML = data.message;
             }
             return;
        }

        // Update progress bar
        const bar = document.getElementById("progressBar");
        if (bar) bar.style.width = `${(data.index / data.total) * 100}%`;

        // Update author stats if available
        if (data.total_posts) {
            const authorStats = document.getElementById("authorTrackerStats");
            if (authorStats) {
                authorStats.innerHTML = `
                    <span class="badge">Post ${data.post_idx} / ${data.total_posts}</span>
                    <span class="badge">Account ${data.index} / ${data.total}</span>
                `;
            }
            if (bar) bar.style.width = `${((data.post_idx - 1) / data.total_posts * 100) + ((data.index / data.total) * (100 / data.total_posts))}%`;
        }

        // Add progress item
        const items = document.getElementById("progressItems");
        if (items) {
            const actionBadges = data.results
                ? Object.entries(data.results).map(([k, v]) =>
                    `<span class="progress-action-badge ${v ? 'ok' : 'fail'}">${k}: ${v ? '✓' : '✗'}</span>`
                ).join("")
                : data.detail || "";

            items.innerHTML += `
                <div class="progress-item ${data.total_posts ? 'author-post-item' : ''}">
                    ${data.total_posts ? `<span class="progress-post-badge">Post ${data.post_idx}</span>` : ''}
                    <span class="progress-phone">${data.phone}</span>
                    <span class="progress-status ${data.status}">${data.status}</span>
                    <div class="progress-actions">${actionBadges}</div>
                </div>
            `;
            items.scrollTop = items.scrollHeight;
        }

        const dotClass = data.status === "success" ? "success" : data.status === "error" ? "error" : "warning";
        addActivity(dotClass, `<strong>${data.phone}</strong> — ${data.status} (${data.index}/${data.total})`);
    }
    else if (data.type === "task_done") {
        addActivity("success", `Task <strong>${data.label}</strong> done: ${data.ok} ✅ ${data.fail} ❌`);
        refreshStats();

        const progress = document.getElementById("taskProgress");
        if (progress) {
            const existing = progress.innerHTML;
            progress.innerHTML = existing + `
                <div class="progress-summary">
                    <div class="summary-stat"><strong>${data.ok}</strong>Success</div>
                    <div class="summary-stat"><strong>${data.fail}</strong>Failed</div>
                    <div class="summary-stat"><strong>${data.total}</strong>Total</div>
                </div>
            `;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
//  ACTIVITY FEED
// ═══════════════════════════════════════════════════════════════════
function addActivity(type, html) {
    const feed = document.getElementById("activityFeed");
    if (!feed) return;

    // Remove empty state
    const empty = feed.querySelector(".empty-state");
    if (empty) empty.remove();

    const item = document.createElement("div");
    item.className = "activity-item";
    item.innerHTML = `
        <div class="activity-dot ${type}"></div>
        <div>
            <div class="activity-text">${html}</div>
            <div class="activity-time">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    feed.prepend(item);

    // Keep max 30
    while (feed.children.length > 30) feed.lastChild.remove();
}

// ═══════════════════════════════════════════════════════════════════
//  MODALS
// ═══════════════════════════════════════════════════════════════════
function openModal(id) {
    document.getElementById(id).classList.add("show");
}

function closeModal(id) {
    document.getElementById(id).classList.remove("show");
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-overlay")) {
        e.target.classList.remove("show");
    }
});

// ═══════════════════════════════════════════════════════════════════
//  TOAST
// ═══════════════════════════════════════════════════════════════════
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || "ℹ️"}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("hide");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ═══════════════════════════════════════════════════════════════════
//  SETTINGS
// ═══════════════════════════════════════════════════════════════════
async function clearAllData() {
    if (!confirm("Delete ALL accounts and logs? This cannot be undone.")) return;
    const data = await apiFetch("/api/accounts");
    if (data?.accounts) {
        for (const acc of data.accounts) {
            await apiFetch(`/api/accounts/${acc.phone}`, { method: "DELETE" });
        }
    }
    showToast("All data cleared", "success");
    refreshStats();
    loadAccounts();
}

// ═══════════════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════════════
function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function timeAgo(ts) {
    if (!ts) return "unknown";
    const diff = Date.now() / 1000 - ts;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard!", "success");
    }).catch(() => {
        showToast("Copy failed", "error");
    });
}
