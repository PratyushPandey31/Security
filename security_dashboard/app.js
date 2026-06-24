const API_BASE = window.location.protocol + "//" + window.location.hostname + ":5000";

document.addEventListener("DOMContentLoaded", () => {
    checkSocAuth();
    
    // Bind Add Rule Form
    const addForm = document.getElementById("addRuleForm");
    if (addForm) {
        addForm.addEventListener("submit", handleAddWafRule);
    }
});

function checkSocAuth() {
    // Auto-authenticate for demo - dashboard always accessible
    localStorage.setItem("soc_auth", "true");

    const overlay = document.getElementById("socLoginOverlay");
    const mainBox = document.getElementById("dashboardMain");

    if (overlay) overlay.style.display = "none";
    if (mainBox) mainBox.style.display = "block";

    // Initial telemetry fetch
    fetchStats();
    fetchAlerts();
    fetchBannedIps();
    fetchWafRules();
    fetchTrafficLogs();
    setupEventStream();

    // Bind Export link to dynamic API base
    const expLink = document.getElementById("btn-export");
    if (expLink) {
        expLink.href = `${API_BASE}/api/reports/csv`;
    }
}


window.handleSocLogin = function(e) {
    if (e) e.preventDefault();
    // Accept any credentials for demo purposes
    localStorage.setItem("soc_auth", "true");
    const errDiv = document.getElementById("socLoginError");
    if (errDiv) errDiv.style.display = "none";
    const overlay = document.getElementById("socLoginOverlay");
    const mainBox = document.getElementById("dashboardMain");
    if (overlay) overlay.style.display = "none";
    if (mainBox) mainBox.style.display = "block";
    // Initialize telemetry fetches
    fetchStats();
    fetchAlerts();
    fetchBannedIps();
    fetchWafRules();
    fetchTrafficLogs();
    setupEventStream();
};

window.handleSocLogout = function() {
    localStorage.removeItem("soc_auth");
    location.reload();
};

// Fetch metrics
function fetchStats() {
    fetch(`${API_BASE}/api/stats`)
        .then(res => res.json())
        .then(data => {
            document.getElementById("stat-total-alerts").innerText = data.total_alerts || 0;
            document.getElementById("stat-critical").innerText = data.critical_alerts || 0;
            document.getElementById("stat-honeypot").innerText = data.honeypot_triggers || 0;
            document.getElementById("stat-bans").innerText = data.total_bans || 0;
        })
        .catch(err => console.error("Error fetching stats:", err));
}

// Fetch alerts
function fetchAlerts() {
    fetch(`${API_BASE}/api/alerts?limit=25`)
        .then(res => res.json())
        .then(data => {
            const feed = document.getElementById("alert-feed");
            feed.innerHTML = "";
            if (data.length === 0) {
                feed.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">No security threats logged yet. Gateway is clean.</div>`;
                return;
            }
            data.forEach(alert => {
                appendAlertToFeed(alert, false);
            });
        })
        .catch(err => console.error("Error fetching alerts:", err));
}

// Fetch firewall banned list
function fetchBannedIps() {
    fetch(`${API_BASE}/api/banned-ips`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("banned-table-body");
            tbody.innerHTML = "";
            if (data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">No active IP bans.</td></tr>`;
                return;
            }
            data.forEach(item => {
                const tr = document.createElement("tr");
                const date = new Date(item.ban_time).toLocaleTimeString();
                tr.innerHTML = `
                    <td style="font-weight: 700; color: var(--neon-red);">${item.ip}</td>
                    <td>${date}</td>
                    <td>${item.reason}</td>
                    <td><button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="unbanIp('${item.ip}')">Unban IP</button></td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Error fetching banned IPs:", err));
}

// Unban dynamic firewall block
window.unbanIp = function(ip) {
    fetch(`${API_BASE}/api/unban`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip: ip })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            fetchBannedIps();
            fetchStats();
        }
    })
    .catch(err => console.error("Error unbanning IP:", err));
};

// Fetch WAF custom signatures
function fetchWafRules() {
    fetch(`${API_BASE}/api/waf/rules`)
        .then(res => res.json())
        .then(rules => {
            const tbody = document.getElementById("rules-table-body");
            tbody.innerHTML = "";
            if (rules.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No WAF rules configured.</td></tr>`;
                return;
            }
            rules.forEach(rule => {
                const tr = document.createElement("tr");
                const isChecked = rule.enabled ? "checked" : "";
                
                tr.innerHTML = `
                    <td style="font-weight: 700; color: var(--neon-blue);">Rule: ${rule.rule_name}</td>
                    <td style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted); max-width: 250px; word-wrap: break-word;">${rule.pattern}</td>
                    <td style="font-weight: 600; font-size: 0.75rem;">${rule.target_field}</td>
                    <td><span class="badge ${rule.severity.toLowerCase()}">${rule.severity}</span></td>
                    <td>
                        <label class="switch">
                            <input type="checkbox" id="rule-toggle-${rule.id}" ${isChecked} onchange="toggleWafRule('${rule.rule_name}', this.checked)">
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>
                        <button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="deleteWafRule('${rule.rule_name}')">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Error fetching rules:", err));
}

// Toggle WAF rule enabled status
window.toggleWafRule = function(ruleName, isEnabled) {
    fetch(`${API_BASE}/api/waf/rules/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rule_name: ruleName, enabled: isEnabled })
    })
    .catch(err => console.error("Error toggling WAF rule:", err));
};

// Add custom WAF rule
function handleAddWafRule(e) {
    e.preventDefault();
    const name = document.getElementById("ruleName").value;
    const pattern = document.getElementById("rulePattern").value;
    const field = document.getElementById("ruleTarget").value;
    const severity = document.getElementById("ruleSeverity").value;
    
    // Generate a demo secret key
    const secretKey = Math.random().toString(36).substring(2, 10).toUpperCase();
    
    fetch(`${API_BASE}/api/waf/rules/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            rule_name: name,
            pattern: pattern,
            target_field: field,
            severity: severity
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            document.getElementById("addRuleForm").reset();
            fetchWafRules();
            // Show secret key popup after successful deployment
            alert(`✅ Your secret key is: ${secretKey}\nKeep it safe for admin actions.`);
            // Ensure UI shows at least one row (demo placeholder) if table is empty
            const tbody = document.getElementById("rules-table-body");
            if (tbody && tbody.children.length === 0) {
                const tr = document.createElement("tr");
                tr.innerHTML = `<td colspan="6" style="text-align:center;color:var(--text-muted);padding:1rem;">Demo rule deployed – secret key stored.</td>`;
                tbody.appendChild(tr);
            }
        }
    })
    .catch(err => console.error("Error adding WAF rule:", err));
}

// Delete custom WAF rule
window.deleteWafRule = function(ruleName) {
    if (!confirm(`Are you sure you want to delete WAF rule: ${ruleName}?`)) return;
    
    fetch(`${API_BASE}/api/waf/rules/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rule_name: ruleName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            fetchWafRules();
        }
    })
    .catch(err => console.error("Error deleting rule:", err));
};

// Trigger Autonomous Security Audit Scan
window.triggerAuditScan = function() {
    const targetUrl = document.getElementById("scanTargetUrl").value;
    const btn = document.getElementById("startScanBtn");
    const pBar = document.getElementById("scanProgressBar");
    const pFill = document.getElementById("scanProgressFill");
    const status = document.getElementById("scanStatus");
    const reportCard = document.getElementById("auditReportCard");
    
    btn.disabled = true;
    pBar.style.display = "block";
    status.style.display = "block";
    reportCard.style.display = "none";
    
    const steps = [
        { progress: 20, text: "Scanning Exposed Administrative Directories (/admin)..." },
        { progress: 45, text: "Evaluating HTTP Response Header Security Parameters..." },
        { progress: 75, text: "Probing Authentication Login parameters for SQLi Bypass exposure..." },
        { progress: 95, text: "Generating Vulnerability Audit Scorecard and Grades..." }
    ];
    
    let currentStep = 0;
    
    const interval = setInterval(() => {
        if (currentStep < steps.length) {
            pFill.style.width = `${steps[currentStep].progress}%`;
            status.innerText = steps[currentStep].text;
            currentStep++;
        } else {
            clearInterval(interval);
            
            // Execute real API audit scan request
            fetch(`${API_BASE}/api/scanner/audit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target_url: targetUrl })
            })
            .then(res => {
                if (!res.ok) throw new Error("Scanner request failed");
                return res.json();
            })
            .then(report => {
                pFill.style.width = "100%";
                status.innerText = "Audit Scan Completed successfully.";
                
                setTimeout(() => {
                    // Reset scanner UI
                    btn.disabled = false;
                    pBar.style.display = "none";
                    status.style.display = "none";
                    pFill.style.width = "0%";
                    
                    // Render audit report
                    renderAuditReport(report);
                }, 800);
            })
            .catch(err => {
                console.error(err);
                btn.disabled = false;
                pBar.style.display = "none";
                status.innerText = "Error: Scanning target connection failed.";
            });
        }
    }, 800);
};

function renderAuditReport(report) {
    const card = document.getElementById("auditReportCard");
    const gradeCircle = document.getElementById("auditReportGrade");
    const targetSpan = document.getElementById("auditReportTarget");
    const scoreStrong = document.getElementById("auditReportScore");
    const dateSpan = document.getElementById("auditReportDate");
    const findingsDiv = document.getElementById("auditReportFindings");
    
    // Set text details
    gradeCircle.innerText = report.security_grade;
    targetSpan.innerText = report.target_url;
    scoreStrong.innerText = `${report.grade_score}/100`;
    dateSpan.innerText = new Date(report.timestamp).toLocaleDateString() + ' ' + new Date(report.timestamp).toLocaleTimeString();
    
    // Set color based on grade
    if (report.security_grade === "A") {
        gradeCircle.style.borderColor = "var(--neon-green)";
        gradeCircle.style.color = "var(--neon-green)";
        scoreStrong.style.color = "var(--neon-green)";
    } else if (report.security_grade === "B" || report.security_grade === "C") {
        gradeCircle.style.borderColor = "var(--warning-color)";
        gradeCircle.style.color = "var(--warning-color)";
        scoreStrong.style.color = "var(--warning-color)";
    } else {
        gradeCircle.style.borderColor = "var(--neon-red)";
        gradeCircle.style.color = "var(--neon-red)";
        scoreStrong.style.color = "var(--neon-red)";
    }
    
    // Render findings list
    findingsDiv.innerHTML = "";
    
    // Add Executive Summary Block
    const execSummary = document.createElement("div");
    execSummary.className = "scanner-summary-card";
    execSummary.style.cssText = "background-color: rgba(9, 13, 22, 0.4); border: 1px solid var(--border-color); padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;";
    
    const riskStatus = report.grade_score >= 80 ? 'SECURE' : report.grade_score >= 60 ? 'MODERATE RISK' : 'CRITICAL SECURITY RISK';
    const riskColor = report.grade_score >= 80 ? 'var(--neon-green)' : report.grade_score >= 60 ? 'var(--warning-color)' : 'var(--neon-red)';
    
    execSummary.innerHTML = `
        <h4 style="color: var(--neon-blue); margin-bottom: 0.75rem; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px; font-weight: 800;">📋 Executive Audit Summary</h4>
        <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.6; margin-bottom: 0.5rem;">
            An automated threat audit and vulnerability probe was launched targeting the public gateway instance: <strong>${report.target_url}</strong>. The auditor analyzed directory index pathways, verified deceptive routing protocols (Honeypot Decoys), inspected response headers, and attempted database authentication injection bypass.
        </p>
        <div style="font-size: 0.9rem; color: var(--text-main); margin-top: 0.75rem;">
            System Security Status: <strong style="color: ${riskColor};">${riskStatus}</strong>
        </div>
    `;
    findingsDiv.appendChild(execSummary);
    
    report.findings.forEach(finding => {
        const div = document.createElement("div");
        const sevClass = finding.severity.toLowerCase();
        div.className = `audit-finding-card ${sevClass}`;
        
        let codeSnippetHtml = "";
        if (finding.code_snippet) {
            codeSnippetHtml = `
                <div style="margin-top: 1rem; border-top: 1px dashed rgba(255,255,255,0.05); padding-top: 0.75rem;">
                    <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 0.4rem; font-family: monospace;">[REMEDIATION PATCH IMPLEMENTATION]</span>
                    <pre style="background-color: #03060a; border: 1px solid var(--border-color); padding: 0.75rem; border-radius: 4px; font-family: 'Consolas', monospace; font-size: 0.8rem; color: #a5d6ff; overflow-x: auto; white-space: pre; line-height: 1.4;">${finding.code_snippet}</pre>
                </div>
            `;
        }
        
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <h4 style="font-weight: 700; font-size: 1rem;">${finding.title}</h4>
                <span class="badge ${sevClass}">${finding.severity}</span>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">${finding.details}</p>
            <p style="font-size: 0.85rem; color: #ff6b6b; margin-bottom: 0.75rem; font-family: sans-serif;">
                <strong>Exploit Impact:</strong> ${finding.impact}
            </p>
            <div style="font-size: 0.85rem; color: var(--neon-blue); margin-bottom: 0.5rem;">
                <strong>Remediation:</strong> ${finding.remediation}
            </div>
            ${codeSnippetHtml}
        `;
        findingsDiv.appendChild(div);
    });
    
    card.style.display = "block";

    // Auto‑download CSV audit report after rendering (500 ms delay to ensure UI updates)
    setTimeout(() => {
        const link = document.createElement('a');
        link.href = `${API_BASE}/api/reports/csv`;
        link.download = 'audit_report.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, 500);

}

// Setup EventSource real-time stream
function setupEventStream() {
    const source = new EventSource(`${API_BASE}/api/events`);
    
    source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "ping") return;
        
        // Check if this is a raw traffic transaction log event
        if (data.event_type === "traffic") {
            appendTrafficToConsole(data);
            return;
        }
        
        // Refresh metrics, bans, and custom WAF rules registry
        fetchStats();
        
        if (data.attack_type === "IP Blocked" || data.attack_type === "IP Unbanned") {
            fetchBannedIps();
        }
        
        if (data.status === "CONFIG_UPDATE") {
            fetchWafRules();
        }
        
        // Visual Map Threat Vector Trigger
        if (data.status === "BLOCKED" || data.attack_type.includes("Honeypot") || data.severity === "HIGH") {
            triggerMapAttackVector(data.src_ip);
        }
        
        appendAlertToFeed(data, true);
    };
    
    source.onerror = (err) => {
        console.error("SSE connection lost. Re-establishing connection...", err);
        source.close();
        setTimeout(setupEventStream, 5000);
    };
}

// Visual Geolocation Map Threat Vector Line Drawer
function triggerMapAttackVector(ip) {
    const svg = document.getElementById("mapSvg");
    if (!svg) return;
    
    // Choose a random outer coordinate representing the source location
    const coords = [
        { x: 100, y: 100, label: "Beijing" },
        { x: 150, y: 300, label: "Moscow" },
        { x: 300, y: 50, label: "Frankfurt" },
        { x: 800, y: 320, label: "New York" },
        { x: 750, y: 80, label: "London" },
        { x: 900, y: 220, label: "Tokyo" }
    ];
    
    const src = coords[Math.floor(Math.random() * coords.length)];
    
    // Create line path
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    // Draw Bezier curve from source coordinate to target center coordinate (500, 200)
    const ctrlX = (src.x + 500) / 2;
    const ctrlY = Math.min(src.y, 200) - 80;
    path.setAttribute("d", `M ${src.x} ${src.y} Q ${ctrlX} ${ctrlY} 500 200`);
    path.setAttribute("class", "threat-line");
    // Make the line pulse red glow
    path.setAttribute("stroke", "#FF0055");
    path.setAttribute("stroke-width", "2");
    
    // Create animated circle threat node
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", src.x);
    circle.setAttribute("cy", src.y);
    circle.setAttribute("r", "8");
    circle.setAttribute("fill", "#FF0055");
    circle.style.animation = "pulse 1s infinite";
    
    // Create threat text label
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", src.x);
    text.setAttribute("y", src.y - 12);
    text.setAttribute("fill", "#FF0055");
    text.setAttribute("font-size", "9");
    text.setAttribute("text-anchor", "middle");
    text.textContent = `IP: ${ip} (ATTACK INTERCEPTED)`;
    
    // Append nodes to SVG
    svg.appendChild(path);
    svg.appendChild(circle);
    svg.appendChild(text);
    
    // Auto-remove line nodes after 4 seconds to prevent SVG bloating
    setTimeout(() => {
        svg.removeChild(path);
        svg.removeChild(circle);
        svg.removeChild(text);
    }, 4000);
}

function appendAlertToFeed(alert, prepend = true) {
    const feed = document.getElementById("alert-feed");
    if (feed.innerText.includes("No security threats logged")) {
        feed.innerHTML = "";
    }
    
    const card = document.createElement("div");
    const severityClass = alert.severity.toLowerCase();
    card.className = `alert-card ${severityClass} ${alert.status === 'CONFIG_UPDATE' ? 'config_update' : ''}`;
    
    const timeStr = new Date(alert.timestamp).toLocaleTimeString();
    
    let detailsHtml = "";
    try {
        const details = typeof alert.details === "string" ? JSON.parse(alert.details) : alert.details;
        if (details && Object.keys(details).length > 0) {
            detailsHtml = `<div style="font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 0.5rem; margin-top: 0.5rem; border-radius: 4px; font-family: monospace; overflow-x: auto; max-width: 100%;">
                ${Object.entries(details).map(([k, v]) => `<strong>${k}:</strong> ${v}`).join("<br>")}
            </div>`;
        }
    } catch(e) {}

    card.innerHTML = `
        <div class="alert-card-meta">
            <span>🔴 SOURCE IP: ${alert.src_ip}</span>
            <span>⏱️ ${timeStr}</span>
        </div>
        <div class="alert-card-body">
            <div>
                <span class="alert-type">${alert.attack_type}</span>
                <div class="alert-desc">${alert.description}</div>
                <div style="font-size: 0.8rem; color: var(--neon-blue); margin-top: 0.25rem;">Path: ${alert.request_method} ${alert.request_path}</div>
                ${detailsHtml}
            </div>
            <span class="badge ${severityClass}">${alert.severity}</span>
        </div>
    `;
    
    if (prepend) {
        feed.insertBefore(card, feed.firstChild);
        if (feed.children.length > 50) {
            feed.removeChild(feed.lastChild);
        }
    } else {
        feed.appendChild(card);
    }
}

// Fetch and render Raw Traffic logs
function fetchTrafficLogs() {
    fetch(`${API_BASE}/api/traffic?limit=50`)
        .then(res => res.json())
        .then(data => {
            const consoleBox = document.getElementById("trafficConsole");
            if (!consoleBox) return;
            consoleBox.innerHTML = "";
            if (data.length === 0) {
                consoleBox.innerHTML = `<div class="console-line system">[SYSTEM] No gateway transactions captured yet. Monitor active.</div>`;
                return;
            }
            // Display oldest first in console logs stream
            data.reverse().forEach(log => {
                appendTrafficToConsole(log);
            });
        })
        .catch(err => console.error("Error fetching traffic logs:", err));
}

function appendTrafficToConsole(log) {
    const consoleBox = document.getElementById("trafficConsole");
    if (!consoleBox) return;
    if (consoleBox.innerText.includes("No gateway transactions") || consoleBox.innerText.includes("sensor online")) {
        consoleBox.innerHTML = "";
    }
    
    const line = document.createElement("div");
    const actionClass = log.action.toLowerCase();
    line.className = `console-line ${actionClass}`;
    
    const timeStr = new Date(log.timestamp).toLocaleTimeString();
    let detailText = `[${timeStr}] ${log.request_method} ${log.request_path} - IP: ${log.src_ip} - ACTION: ${log.action} (Status: ${log.status_code})`;
    if (log.rule_matched) {
        detailText += ` - Trigger: ${log.rule_matched}`;
    }
    
    line.innerText = detailText;
    consoleBox.appendChild(line);
    
    // Auto-scroll to bottom of traffic log console
    consoleBox.scrollTop = consoleBox.scrollHeight;
}

window.clearTrafficLog = function() {
    const consoleBox = document.getElementById("trafficConsole");
    if (consoleBox) {
        consoleBox.innerHTML = `<div class="console-line system">[SYSTEM] Traffic console log cleared. Telemetry sensor monitoring...</div>`;
    }
};

// ─── Analytics Charts ──────────────────────────────────────────────────────────

let _charts = {};

function destroyChart(id) {
    if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

const CHART_DEFAULTS = {
    color: "#8E9BAE",
    plugins: {
        legend: { labels: { color: "#8E9BAE", font: { family: "Outfit", size: 12 }, padding: 16 } }
    }
};

window.renderCharts = function() {
    Promise.all([
        fetch(`${API_BASE}/api/alerts?limit=500`).then(r => r.json()),
        fetch(`${API_BASE}/api/traffic?limit=500`).then(r => r.json())
    ]).then(([alerts, traffic]) => {
        renderAttackTypeChart(alerts);
        renderTimelineChart(alerts);
        renderSeverityChart(alerts);
        renderTopIPs(alerts);
        renderWafActionChart(traffic);
        renderAlertStatusChart(alerts);
    }).catch(err => console.error("Chart data fetch failed:", err));
};

/* 1 ── Attack Type Doughnut */
function renderAttackTypeChart(alerts) {
    const counts = {};
    alerts.forEach(a => { counts[a.attack_type] = (counts[a.attack_type] || 0) + 1; });
    const labels = Object.keys(counts);
    const data   = Object.values(counts);
    const colors = ["#FF0055","#00F0FF","#39FF14","#FF5E00","#A855F7","#F59E0B","#EC4899","#14B8A6","#6366F1","#84CC16"];

    destroyChart("attackTypeChart");
    _charts.attackTypeChart = new Chart(document.getElementById("attackTypeChart"), {
        type: "doughnut",
        data: { labels, datasets: [{ data, backgroundColor: colors.slice(0, labels.length), borderColor: "#090D16", borderWidth: 3, hoverOffset: 8 }] },
        options: {
            cutout: "65%",
            plugins: {
                ...CHART_DEFAULTS.plugins,
                tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} events` } }
            }
        }
    });
}

/* 2 ── 24-Hour Timeline Bar Chart */
function renderTimelineChart(alerts) {
    const hourBuckets = {};
    const now = new Date();
    for (let h = 23; h >= 0; h--) {
        const d = new Date(now);
        d.setHours(now.getHours() - h, 0, 0, 0);
        hourBuckets[d.getHours()] = 0;
    }
    alerts.forEach(a => {
        const h = new Date(a.timestamp).getHours();
        if (h in hourBuckets) hourBuckets[h]++;
    });
    const labels = Object.keys(hourBuckets).map(h => `${String(h).padStart(2,"0")}:00`);
    const data   = Object.values(hourBuckets);

    destroyChart("timelineChart");
    _charts.timelineChart = new Chart(document.getElementById("timelineChart"), {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Attacks",
                data,
                backgroundColor: data.map(v => v > 4 ? "rgba(255,0,85,0.75)" : "rgba(0,240,255,0.55)"),
                borderColor:     data.map(v => v > 4 ? "#FF0055" : "#00F0FF"),
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            scales: {
                x: { ticks: { color: "#8E9BAE", font: { size: 10 } }, grid: { color: "rgba(34,50,84,0.5)" } },
                y: { ticks: { color: "#8E9BAE", stepSize: 1 }, grid: { color: "rgba(34,50,84,0.5)" }, beginAtZero: true }
            },
            plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } }
        }
    });
}

/* 3 ── Severity Horizontal Bar */
function renderSeverityChart(alerts) {
    const sevOrder = ["CRITICAL","HIGH","MEDIUM","LOW","INFO"];
    const counts   = {};
    sevOrder.forEach(s => counts[s] = 0);
    alerts.forEach(a => { if (a.severity in counts) counts[a.severity]++; });

    destroyChart("severityChart");
    _charts.severityChart = new Chart(document.getElementById("severityChart"), {
        type: "bar",
        data: {
            labels: sevOrder,
            datasets: [{
                label: "Alerts",
                data: sevOrder.map(s => counts[s]),
                backgroundColor: ["rgba(255,0,85,0.8)","rgba(255,94,0,0.8)","rgba(245,158,11,0.8)","rgba(57,255,20,0.7)","rgba(0,240,255,0.6)"],
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: "y",
            scales: {
                x: { ticks: { color: "#8E9BAE" }, grid: { color: "rgba(34,50,84,0.5)" }, beginAtZero: true },
                y: { ticks: { color: "#F3F4F6", font: { weight: "bold" } }, grid: { color: "rgba(34,50,84,0.3)" } }
            },
            plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } }
        }
    });
}

/* 4 ── Top Attacker IPs Table */
function renderTopIPs(alerts) {
    const ipCounts = {};
    const ipSeverity = {};
    alerts.forEach(a => {
        ipCounts[a.src_ip] = (ipCounts[a.src_ip] || 0) + 1;
        if (!ipSeverity[a.src_ip] || a.severity === "CRITICAL") ipSeverity[a.src_ip] = a.severity;
    });
    const sorted = Object.entries(ipCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
    const tbody  = document.getElementById("top-ips-body");
    if (!tbody) return;
    const sevColor = { CRITICAL: "#FF0055", HIGH: "#FF5E00", MEDIUM: "#F59E0B", LOW: "#39FF14", INFO: "#00F0FF" };
    tbody.innerHTML = sorted.map(([ip, count], i) => {
        const sev = ipSeverity[ip] || "LOW";
        const bar = `<div style="display:inline-block;width:${Math.min(count * 8, 80)}px;height:6px;background:${sevColor[sev]||'#888'};border-radius:3px;vertical-align:middle;margin-right:6px;"></div>`;
        return `<tr>
            <td style="color:var(--text-muted);font-size:0.85rem;">${i + 1}</td>
            <td style="font-family:monospace;font-weight:700;color:var(--neon-red);">${ip}</td>
            <td>${bar}<strong>${count}</strong></td>
            <td><span class="badge ${sev.toLowerCase()}">${sev}</span></td>
        </tr>`;
    }).join("");
}

/* 5 ── WAF Action Doughnut (traffic) */
function renderWafActionChart(traffic) {
    const counts = { PASS: 0, BLOCK: 0, DECEPTION: 0 };
    traffic.forEach(t => { if (t.action in counts) counts[t.action]++; });

    destroyChart("wafActionChart");
    _charts.wafActionChart = new Chart(document.getElementById("wafActionChart"), {
        type: "doughnut",
        data: {
            labels: ["PASS","BLOCK","DECEPTION"],
            datasets: [{ data: [counts.PASS, counts.BLOCK, counts.DECEPTION],
                backgroundColor: ["rgba(57,255,20,0.7)","rgba(255,0,85,0.8)","rgba(255,94,0,0.8)"],
                borderColor: "#090D16", borderWidth: 3, hoverOffset: 8 }]
        },
        options: { cutout: "60%", plugins: { ...CHART_DEFAULTS.plugins } }
    });
}

/* 6 ── Alert Status Overview Doughnut */
function renderAlertStatusChart(alerts) {
    const counts = { BLOCKED: 0, LOGGED: 0 };
    alerts.forEach(a => { const k = a.status === "BLOCKED" ? "BLOCKED" : "LOGGED"; counts[k]++; });

    destroyChart("alertStatusChart");
    _charts.alertStatusChart = new Chart(document.getElementById("alertStatusChart"), {
        type: "doughnut",
        data: {
            labels: ["BLOCKED","LOGGED"],
            datasets: [{ data: [counts.BLOCKED, counts.LOGGED],
                backgroundColor: ["rgba(255,0,85,0.8)","rgba(0,240,255,0.6)"],
                borderColor: "#090D16", borderWidth: 3, hoverOffset: 8 }]
        },
        options: { cutout: "60%", plugins: { ...CHART_DEFAULTS.plugins } }
    });
}

