# CloudShield v4: Advanced Cyber Defense, Intrusion Prevention & Deception Suite

Welcome to **CloudShield v4**, a production-grade, zero-trust cloud security and cyber defense virtualization suite. Designed as a comprehensive Security Operations Center (SOC) simulation, CloudShield integrates active web application firewalls (WAF), real-time log streaming, cryptographic at-rest protection, network deception honeypots, and vulnerability penetration scanners into a unified microservices system.

---

## 🌟 Premium Key Features of v4

1. **Standalone Premium Authentication**:
   - Gorgeous standalone `login.html` and `register.html` pages styled with modern glassmorphism, glowing accents, and fluid layouts.
   - **Breached Password Audit**: Checks passwords against common leaked lists to prevent credential stuffing.
   - **Complexity & Entropy Analyzer**: Real-time password complexity bar indicator calculating bits of cryptographic entropy.
   - **MFA Simulator**: Simulated multi-factor token verification layer.

2. **At-Rest Cryptographic Shield (Vault)**:
   - Secure File Vault encrypts user documents at-rest inside SQLite tables.
   - Utilizes portable, fast RC4 stream ciphers with dynamic keys derived from session variables (portal salts combined with user credentials).

3. **Live Gateway Traffic Visualizer**:
   - Real-time logging console on the SIEM dashboard streaming all request traffic (PASS, BLOCK, DECEPTION) from the proxy gateway via Server-Sent Events (SSE).

4. **Interactive 6+ Analytics Charts & Threat Map**:
   - Beautiful, local-first Chart.js layouts showing Attack Distributions, 24-Hour Timeline Bar Charts (with vertical gradients), Severity Risk Matrices, WAF Action ratios, and HTTP Methods.
   - Dynamic animated SVG Threat Maps sketching network lines when threats are blocked.

5. **Autonomous Vulnerability Scanner & Auditor**:
   - Penetration testing tool probing target URLs, checking for missing security response headers (HSTS, CSP, XFO), directory indexing, and SQL injection vulnerabilities.
   - **Executive PDF Scorecard**: Print-optimized assessment reports complete with executive summaries, risk levels, and copy-paste remediation patches (Nginx/Flask code blocks).

6. **Active Deception Honeypots**:
   - Decoy sandbox environment routing directory probes (like `/admin`) away from the real backend.
   - Auto-bans attacker IPs at the firewall layer if command execution exploits (like `whoami` or `cat /etc/shadow`) are attempted.

---

## 🛠️ System Architecture

```text
               +--------------------------------------+
               |          Attacker / Client           |
               +--------------------------------------+
                                   |
                                   | Port 8080 (Traffic Gateway)
                                   v
               +--------------------------------------+
               |      Proxy WAF Gateway (proxy_waf)    |
               +--------------------------------------+
                  /                                \
      Legitimate /                                  \ Suspicious / Admin
      Traffic   /                                    \ Path Request
               v                                      v
+------------------------+                 +------------------------+
|  Legitimate Web App    |                 |     Decoy Honeypot     |
| (web_app with User DB) |                 |    (honeypot_decoy)    |
+------------------------+                 +------------------------+
               \                                    /
                \-------> Log Security Alert <-----/
                                 |
                                 v
               +--------------------------------------+
               |   Security Database & API Backend    |
               |       (security_backend:5000)        |
               +--------------------------------------+
                                 ^
                                 | Port 5000 (REST / SSE Feed)
                                 v
               +--------------------------------------+
               |     SIEM Dashboard UI Server         |
               |      (security_dashboard:8081)       |
               +--------------------------------------+
```

---

## 🚀 Step-by-Step Setup Guide

### 📦 Start Natively using Python (Easiest)
Launch all 5 microservices (Backend API, Legitimate App, Decoy Honeypot, WAF Proxy Gateway, and SIEM Dashboard) natively using Python. The startup script checks and installs required dependencies (`flask`, `requests`) automatically.

1. Open a PowerShell/Terminal window in the project root directory and run:
   ```bash
   python run_locally.py
   ```
2. Keep this window running. To stop all services cleanly, press `Ctrl+C` in the terminal.

### 🐳 Start using Docker Compose
If Docker Desktop is running on your host system:
1. Build and boot the container network:
   ```bash
   docker compose up --build -d
   ```
2. View container statuses:
   ```bash
   docker ps
   ```
3. Tear down the containers:
   ```bash
   docker compose down
   ```

---

## 💻 Live Demonstration Walkthrough

Perform these steps during presentations to illustrate CloudShield's active defense capabilities:

### Step 1: Open portals
- **WAF Proxy Gateway (App)**: [http://localhost:8080](http://localhost:8080)
- **SIEM SOC Dashboard**: [http://localhost:8081](http://localhost:8081)

### Step 2: Test Password Auditing & Sign Up
1. Go to the app signup: [http://localhost:8080/register](http://localhost:8080/register).
2. Type a common password (e.g., `admin1234`). Note the indicator bar shows **Weak**.
3. Create a strong credentials set (e.g., `SafeAdmin!99` -> **Excellent**). Complete the registration.

### Step 3: Test Login & MFA Simulator
1. Go to the sign-in page: [http://localhost:8080/login](http://localhost:8080/login).
2. Type your registered username and password. Click **Verify Identity**.
3. The MFA screen prompts. Copy the simulated token code shown on the screen and paste it in the field to log in.
4. Navigate the sidebar tabs, especially **Security Rating** and **Security Features**.

### Step 4: Encrypted Vault Demonstration
1. In the user portal, select **Secure File Vault**.
2. Upload a note (e.g. `filename: keys.txt`, `content: secret123`).
3. Under the list, click **View raw database payload** to show examiners that the content is stored completely encrypted inside the SQLite database, but decrypts dynamically in the active user console.

### Step 5: Test WAF Block & Real-Time Alert Logging
1. Go back to the SIEM Dashboard. Ensure the SQL Injection and XSS rules are **enabled** (Signature Registry tab).
2. Go to the web app sign-in page.
3. Try an SQL Injection login bypass payload in the username field: `' OR 1=1--`.
4. Click **Verify Identity**.
5. **Result**: Instantly intercepted! The gateway returns a red **Access Blocked** screen.
6. Open the SIEM Dashboard. Notice the new SQL Injection alert in the real-time feed, and the live request logged in the **Traffic Inspector** console!

### Step 6: Decoy Redirect & Automated IP Ban
1. Probing decoy: Visit [http://localhost:8080/admin](http://localhost:8080/admin) in the browser.
2. The WAF gateway redirects the request to the isolated **Honeypot Decoy console**.
3. Inside the honeypot terminal, attempt an exploit command (e.g., `cat /etc/shadow` or `whoami`).
4. **Result**: The honeypot logs the command execution, sends a CRITICAL alert to the backend, and the backend triggers a firewall-layer ban on the source IP.
5. Try to refresh the main website homepage ([http://localhost:8080](http://localhost:8080)). You are blocked from the network!
6. Visit the SIEM Dashboard, click the **Firewall Blocklist** tab, and click **Unban** to restore access.

### Step 7: Run Vulnerability Scan & Export Report
1. On the SIEM Dashboard, navigate to the **Vulnerability Auditor** tab.
2. Click **Start Scan** targeting `http://localhost:8080`.
3. Review the scorecard (Missing headers, exposed paths, and bypass tests).
4. Click **Print** to save or print the executive audit report, or inspect the auto-downloaded audit CSV sheet.
