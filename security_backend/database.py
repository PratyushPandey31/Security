import sqlite3
import os
from datetime import datetime

DB_DIR = "/app/data" if os.path.exists("/app/data") else "data"
DB_PATH = os.path.join(DB_DIR, "security.db")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Alerts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            src_ip TEXT NOT NULL,
            attack_type TEXT NOT NULL,
            request_path TEXT NOT NULL,
            request_method TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT,
            details TEXT,
            status TEXT DEFAULT 'LOGGED'
        )
    ''')
    
    # 2. Banned IPs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_ips (
            ip TEXT PRIMARY KEY,
            ban_time TEXT NOT NULL,
            reason TEXT
        )
    ''')
    
    # 3. Dynamic WAF Signatures Table (WAF Custom Rules Builder)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waf_custom_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT UNIQUE NOT NULL,
            pattern TEXT NOT NULL,
            target_field TEXT NOT NULL, -- 'QUERY_OR_BODY', 'PATH', 'HEADERS'
            severity TEXT DEFAULT 'HIGH',
            enabled INTEGER DEFAULT 1
        )
    ''')
    
    # 4. Raw Traffic Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_traffic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            src_ip TEXT NOT NULL,
            request_path TEXT NOT NULL,
            request_method TEXT NOT NULL,
            action TEXT NOT NULL, -- 'PASS', 'BLOCK', 'DECEPTION'
            rule_matched TEXT,
            status_code INTEGER
        )
    ''')
    
    # Populate Default Rules
    default_rules = [
        ("SQL Injection", "(?i)(UNION\\s+SELECT|UNION\\s+ALL\\s+SELECT|' OR 1=1|--|/\\*|\\*/|OR\\s+'\\w+'\\s*=\\s*'\\w+')", "QUERY_OR_BODY", "HIGH", 1),
        ("Cross-Site Scripting (XSS)", "(?i)(<script|javascript:|onload\\s*=|onerror\\s*=|alert\\(|eval\\()", "QUERY_OR_BODY", "HIGH", 1),
        ("Path Traversal (LFI)", "(?i)(\\.\\./|\\.\\.\\\\|/etc/passwd|/windows/win\\.ini|/win\\.ini)", "QUERY", "HIGH", 1)
    ]
    for name, pattern, field, sev, state in default_rules:
        cursor.execute('''
            INSERT OR IGNORE INTO waf_custom_rules (rule_name, pattern, target_field, severity, enabled)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, pattern, field, sev, state))
        
    # Populate Default Alerts for Demo
    cursor.execute('SELECT COUNT(*) FROM alerts')
    if cursor.fetchone()[0] == 0:
        import json
        from datetime import datetime, timedelta
        
        # Insert 6 mock threat alerts from different geolocations
        mock_alerts = [
            (
                (datetime.now() - timedelta(minutes=45)).isoformat(),
                "198.51.100.4",
                "SQL Injection",
                "/login",
                "POST",
                "HIGH",
                "Autonomous dynamic block: Rule [SQL Injection] triggered in request field [QUERY_OR_BODY].",
                json.dumps({"matched_signature": "(?i)(UNION\\s+SELECT|' OR 1=1)", "payload": "username=admin' OR '1'='1"}),
                "BLOCKED"
            ),
            (
                (datetime.now() - timedelta(minutes=30)).isoformat(),
                "221.228.1.9",
                "Cross-Site Scripting (XSS)",
                "/register",
                "POST",
                "HIGH",
                "Autonomous dynamic block: Rule [Cross-Site Scripting (XSS)] triggered in request field [QUERY_OR_BODY].",
                json.dumps({"matched_signature": "(?i)(<script)", "payload": "username=<script>alert(1)</script>"}),
                "BLOCKED"
            ),
            (
                (datetime.now() - timedelta(minutes=15)).isoformat(),
                "95.104.2.14",
                "Path Traversal (LFI)",
                "/index",
                "GET",
                "HIGH",
                "Autonomous dynamic block: Rule [Path Traversal (LFI)] triggered in request field [QUERY].",
                json.dumps({"matched_signature": "(?i)(\\.\\./)", "payload": "file=../../../../etc/passwd"}),
                "BLOCKED"
            ),
            (
                (datetime.now() - timedelta(minutes=10)).isoformat(),
                "185.220.101.5",
                "Honeypot Discovery",
                "/admin",
                "GET",
                "MEDIUM",
                "User accessed honeypot entry page.",
                json.dumps({"user_agent": "Mozilla/5.0 (compatible; Nmap Scripting Engine)"}),
                "LOGGED"
            ),
            (
                (datetime.now() - timedelta(minutes=5)).isoformat(),
                "185.220.101.5",
                "Honeypot Command Execution",
                "/admin/execute",
                "POST",
                "CRITICAL",
                "Attacker tried executing shell command: 'whoami'",
                json.dumps({"command": "whoami", "output_returned": "root"}),
                "LOGGED"
            )
        ]
        
        cursor.executemany('''
            INSERT INTO alerts (timestamp, src_ip, attack_type, request_path, request_method, severity, description, details, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', mock_alerts)
        
    # Populate Default Raw Traffic for Demo
    cursor.execute('SELECT COUNT(*) FROM raw_traffic')
    if cursor.fetchone()[0] == 0:
        from datetime import datetime, timedelta
        mock_traffic = [
            ((datetime.now() - timedelta(minutes=2)).isoformat(), "127.0.0.1", "/", "GET", "PASS", None, 200),
            ((datetime.now() - timedelta(minutes=2)).isoformat(), "127.0.0.1", "/login", "GET", "PASS", None, 200),
            ((datetime.now() - timedelta(minutes=1)).isoformat(), "127.0.0.1", "/vault", "GET", "PASS", None, 200),
            ((datetime.now() - timedelta(seconds=30)).isoformat(), "127.0.0.1", "/admin", "GET", "DECEPTION", "Honeypot Decoy Redirect", 302)
        ]
        cursor.executemany('''
            INSERT INTO raw_traffic (timestamp, src_ip, request_path, request_method, action, rule_matched, status_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', mock_traffic)
        
    conn.commit()
    conn.close()

# WAF Custom Rules helper functions
def get_custom_rules():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM waf_custom_rules')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_custom_rule(rule_name, pattern, target_field, severity):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO waf_custom_rules (rule_name, pattern, target_field, severity, enabled)
            VALUES (?, ?, ?, ?, 1)
        ''', (rule_name, pattern, target_field, severity))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error adding custom WAF rule: {e}")
        success = False
    finally:
        conn.close()
    return success

def delete_custom_rule(rule_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM waf_custom_rules WHERE rule_name = ?', (rule_name,))
    conn.commit()
    conn.close()

def toggle_custom_rule(rule_name, enabled):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    state_val = 1 if enabled else 0
    cursor.execute('UPDATE waf_custom_rules SET enabled = ? WHERE rule_name = ?', (state_val, rule_name))
    conn.commit()
    conn.close()

def add_alert(src_ip, attack_type, request_path, request_method, severity, description, details, status='LOGGED'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO alerts (timestamp, src_ip, attack_type, request_path, request_method, severity, description, details, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, src_ip, attack_type, request_path, request_method, severity, description, details, status))
    conn.commit()
    conn.close()

def ban_ip(ip, reason):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    ban_time = datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO banned_ips (ip, ban_time, reason)
            VALUES (?, ?, ?)
        ''', (ip, ban_time, reason))
        conn.commit()
    except Exception as e:
        print(f"Error banning IP: {e}")
    finally:
        conn.close()

def unban_ip(ip):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banned_ips WHERE ip = ?', (ip,))
    conn.commit()
    conn.close()

def is_ip_banned(ip):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM banned_ips WHERE ip = ?', (ip,))
    banned = cursor.fetchone() is not None
    conn.close()
    return banned

def get_all_alerts(limit=100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alerts ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_banned_ips():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM banned_ips ORDER BY ban_time DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM alerts')
    total_alerts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM banned_ips')
    total_bans = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE attack_type LIKE '%Honeypot%'")
    honeypot_triggers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts WHERE severity = 'CRITICAL'")
    critical_alerts = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_alerts": total_alerts,
        "total_bans": total_bans,
        "honeypot_triggers": honeypot_triggers,
        "critical_alerts": critical_alerts
    }

def log_traffic(src_ip, request_path, request_method, action, rule_matched=None, status_code=200):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT INTO raw_traffic (timestamp, src_ip, request_path, request_method, action, rule_matched, status_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, src_ip, request_path, request_method, action, rule_matched, status_code))
        conn.commit()
    except Exception as e:
        print(f"Error logging raw traffic to database: {e}")
    finally:
        conn.close()

def get_raw_traffic(limit=100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM raw_traffic ORDER BY id DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching raw traffic: {e}")
        return []
    finally:
        conn.close()
