# 🛡️ CloudShield v4: Enterprise Cyber Defense, Active Deception & Security Audit Suite

[![Security Status](https://img.shields.io/badge/Security-Active%20WAF-brightgreen.svg)](#)
[![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg)](#)
[![License](https://img.shields.io/badge/Architecture-Microservices-orange.svg)](#)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20At--Rest%20Encrypted-purple.svg)](#)

Welcome to **CloudShield v4**, a production-grade, zero-trust cloud security and cyber defense virtualization suite. Architected as a comprehensive Security Operations Center (SOC) simulation, CloudShield integrates active web application firewalls (WAF), live telemetry log streaming, cryptographic at-rest protection, network deception honeypots, and vulnerability penetration scanners into a unified microservices ecosystem.

---

## 🌟 Platform Capabilities & Core Features

### 1. Standalone Premium Authentication & Zero-Trust Portal
*   **Modern Glassmorphic UI**: Independent, sleek `login.html` and `register.html` pages styled with frosted-glass containers, glowing borders, and linear gradient transitions.
*   **Password Entropy Analyzer**: Real-time password complexity checker calculating bits of cryptographic information entropy.
*   **Breached Credentials Audit**: Compares user input against standard dictionary files containing compromised databases to block weak password registrations.
*   **Simulated MFA Generator**: Dynamic 6-digit Multi-Factor Authentication prompt matching standard verification workflows.

### 2. At-Rest Cryptographic Shield (Secure Vault)
*   **Stream Cipher Encryption**: Files uploaded to the portal vault are encrypted at-rest inside SQLite tables.
*   **Session-Key Derivation**: Key combines server secret keys and user session credentials to ensure complete isolation.
*   **Examiner Visualization Tool**: Users can toggle between the decrypted plaintext file and the raw base64-encoded encrypted database payload inside the UI console.

### 3. Real-Time Telemetry Log Streamer
*   **Server-Sent Events (SSE)**: Live HTTP request console displaying network actions (PASS, BLOCK, DECEPTION), response codes, and WAF rules matched as they route.
*   **Visual Threat Vector Tracing**: Dynamic SVG Map plotting threat vectors and drawing glowing attack path lines from geolocations when alerts trigger.

### 4. Interactive 6+ Analytics Visualizations
*   **Custom Chart.js Core**: Locally hosted charts that load without an internet connection, including:
    *   *Attack Distribution Doughnut* (with total count center overlays).
    *   *24-Hour Timeline Bar Chart* (featuring vertical linear gradients).
    *   *Severity Risk Matrix* (horizontal layout).
    *   *WAF Action Ratios* (PASS vs BLOCK vs DECEPTION).
    *   *Alert Status Overview* and *HTTP Methods* breakdowns.

### 5. Pentest Scanner & Executive PDF Report
*   **Multi-Stage Audit Scanner**: Evaluates target URLs for exposed directory indexes (`/admin`), missing security headers (HSTS, CSP, XFO, nosniff), and SQL Injection auth bypasses.
*   **Executive Scorecard**: Automatically generates vulnerability lists and download links for CSV audit logs.
*   **rem-CSS rules**: Print-optimized stylesheets to save scorecards directly as executive PDFs.

### 6. Active Deception Honeypot Sandbox
*   **Transparent Redirection**: Redirects brute force directory probes (like `/admin` or `/wp-admin`) to a decoy sandbox container without throwing error states.
*   **Intrusion Mitigation**: Tracks terminal command executions in the sandbox, automatically triggers firewall-layer bans on the attacker's IP, and generates high-priority alerts.

---

## 📐 Microservices Architecture Map

```text
                               +-------------------------------------+
                               |           Client / Attacker         |
                               +-------------------------------------+
                                                  |
                                                  | Port 8080 (Gateway Proxy)
                                                  v
                               +-------------------------------------+
                               |     Proxy WAF Gateway (proxy_waf)   |
                               +-------------------------------------+
                                  /                               \
                      Legitimate /                                 \ Suspicious / Admin
                      Traffic   /                                   \ Path Request
                               v                                     v
         +---------------------------+                 +---------------------------+
         |    Legitimate Web App     |                 |      Decoy Honeypot       |
         |  (web_app - Users / Vault)|                 |     (honeypot_decoy)      |
         +---------------------------+                 +---------------------------+
                               \                                     /
                                \-------> Send Alert Endpoint <-----/
                                                 |
                                                 v
                               +-------------------------------------+
                               |   Security Database & API Backend   |
                               |       (security_backend:5000)       |
                               +-------------------------------------+
                                                 ^
                                                 | Port 5000 (REST / SSE Feed)
                                                 v
                               +-------------------------------------+
                               |       SIEM SOC Dashboard Server     |
                               |       (security_dashboard:8081)     |
                               +-------------------------------------+
```

---

## 🔌 Microservices Port Configuration

| Service Name | Port | Access URL | Technology Stack |
| :--- | :--- | :--- | :--- |
| **Proxy WAF Gateway** | `8080` | `http://localhost:8080` | Python, Flask, RegEx Rules |
| **Legitimate Web App** | `8000` | `http://localhost:8000` | Python, Flask, Jinja2, SQLite |
| **Deception Honeypot** | `9000` | `http://localhost:9000` | Python, Flask, Mock Terminal |
| **Security Backend API** | `5000` | `http://localhost:5000` | Python, Flask, SQLite, SSE |
| **SIEM Dashboard Server** | `8081` | `http://localhost:8081` | HTML5, Vanilla CSS, Chart.js, SVG |

---

## 🚀 Step-by-Step Setup Guide

### 📦 Option A: Native Startup (Recommended & Easiest)
CloudShield's startup runner installs missing Python packages (`flask`, `requests`) automatically and boots all microservices concurrently.

1. Open a PowerShell/Terminal window in the project root directory and run:
   ```bash
   python run_locally.py
   ```
2. Keep the console window open during the demonstration. Press `Ctrl+C` to stop all services cleanly.

### 🐳 Option B: Docker Compose Container Cluster
If Docker Desktop is running on your host:
1. Build and launch the container nodes:
   ```bash
   docker compose up --build -d
   ```
2. Check container status:
   ```bash
   docker ps
   ```
3. Stop the container swarm:
   ```bash
   docker compose down
   ```

---

## 💻 Live Project Demonstration Walkthrough

Perform the following sequences to showcase the zero-trust active defense mechanics:

### 1. The Zero-Trust Portal Setup & Password Strength Audit
1. Open the website: [http://localhost:8080](http://localhost:8080).
2. Click **Register Secure Account** to access the new `register.html` page.
3. In the password field, type a weak password (e.g. `admin1234`). Note the indicator bar turns red and reads **Weak**.
4. Type a strong credentials string (e.g. `SafeAdmin!99`). The meter updates to green (**Excellent**). Complete the registration.

### 2. Multi-Factor Authentication & Cryptographic Vault
1. Go to the login page: [http://localhost:8080/login](http://localhost:8080/login).
2. Enter your credentials. Click **Verify Identity**.
3. You are redirected to the **MFA Verification** screen. Copy the simulated authentication code, paste it, and verify to login.
4. Select **Secure File Vault** in the dashboard sidebar.
5. Create a file note (e.g. `keys.txt` with content `token_secret_99`).
6. Click **View raw database payload** under the file. This shows examiners the base64-encoded encrypted text stored in the SQLite database to prove **at-rest database encryption**.

### 3. Active WAF Interception & Real-Time Alert Logging
1. Open the **SIEM Dashboard** on [http://localhost:8081](http://localhost:8081) and go to the **Traffic Inspector** tab.
2. In another tab, log out of the portal and go to [http://localhost:8080/login](http://localhost:8080/login).
3. Try a SQL Injection authentication bypass payload:
   * **Username**: `admin' OR '1'='1`
   * **Password**: `any`
4. Click **Verify Identity**.
5. **Result**: The request is instantly blocked by the Proxy WAF Gateway, displaying a red **Access Blocked** alert page.
6. Check the **SIEM Dashboard**. The real-time alert feed shows a new High-Severity SQLi threat, the geolocations map draws a glowing attack vector, and the Traffic Inspector console lists the blocked log live.

### 4. Decoy Redirect & Automated IP Ban
1. Probing decoy: Enter [http://localhost:8080/admin](http://localhost:8080/admin) in the browser.
2. The proxy gateway transparently routes you to the isolated **Mock Honeypot Sandbox**.
3. Inside the terminal prompt, type an exploit command (e.g., `cat /etc/shadow` or `whoami`) and hit Enter.
4. **Result**: The honeypot logs the command execution, alerts the backend, and triggers an **automated firewall ban** on your IP.
5. Try loading the clean homepage [http://localhost:8080/](http://localhost:8080/). You are blocked from the network!
6. Click **Unban IP** in the SIEM dashboard's blocklist table to recover access.

### 5. Vulnerability Scan & PDF Audit Report Generation
1. On the SIEM Dashboard, navigate to the **Vulnerability Auditor** tab.
2. Target `http://localhost:8080` and click **Start Scan**.
3. Once completed, review the security scorecard showing missing headers and SQLi bypass vulnerabilities.
4. Click **Print** to save the scorecard as a formatted executive PDF.
5. Check your downloads directory for the auto-downloaded `audit_report.csv` file containing the complete transaction log.
