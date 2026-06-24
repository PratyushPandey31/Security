from flask import Flask, request, Response, render_template_string
import requests
import re
import os
import json

app = Flask(__name__)

# Configurable endpoints from environment
WEB_APP_URL = os.environ.get('WEB_APP_URL', 'http://127.0.0.1:8000')
HONEYPOT_URL = os.environ.get('HONEYPOT_URL', 'http://127.0.0.1:9000')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://127.0.0.1:5000/api/alerts')

# Paths to redirect silently to decoy honeypot (Deception Technology)
DECOY_PATHS = [
    "/admin",
    "/wp-admin",
    "/phpmyadmin",
    "/config.php",
    "/config",
    "/api/debug",
    "/api/v1/debug",
    "/shell.php",
    "/backup.zip",
    "/.git"
]

def check_ip_banned(ip):
    try:
        check_url = BACKEND_URL.replace('/alerts', '/check-ban')
        res = requests.get(check_url, params={"ip": ip}, timeout=2)
        if res.status_code == 200:
            return res.json().get('banned', False)
    except Exception as e:
        print(f"[Proxy Error] Failed to check ban status with backend: {e}")
    return False

def get_active_rules():
    try:
        rules_url = BACKEND_URL.replace('/alerts', '/waf/rules')
        res = requests.get(rules_url, timeout=2)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"[Proxy Error] Failed to fetch active WAF rules from backend: {e}")
    
    # Fallback default rules
    return [
        {"rule_name": "SQL Injection", "pattern": "(?i)(UNION\\s+SELECT|UNION\\s+ALL\\s+SELECT|' OR 1=1|--|/\\*|\\*/|OR\\s+'\\w+'\\s*=\\s*'\\w+')", "target_field": "QUERY_OR_BODY", "severity": "HIGH", "enabled": 1},
        {"rule_name": "Cross-Site Scripting (XSS)", "pattern": "(?i)(<script|javascript:|onload\\s*=|onerror\\s*=|alert\\(|eval\\()", "target_field": "QUERY_OR_BODY", "severity": "HIGH", "enabled": 1},
        {"rule_name": "Path Traversal (LFI)", "pattern": "(?i)(\\.\\./|\\.\\.\\\\|/etc/passwd|/windows/win\\.ini|/win\\.ini)", "target_field": "QUERY", "severity": "HIGH", "enabled": 1}
    ]

def report_threat(src_ip, attack_type, description, severity, details=None):
    payload = {
        "src_ip": src_ip,
        "attack_type": attack_type,
        "request_path": request.path,
        "request_method": request.method,
        "severity": severity,
        "description": description,
        "details": json.dumps(details or {})
    }
    try:
        requests.post(BACKEND_URL, json=payload, timeout=2)
    except Exception as e:
        print(f"[Proxy Error] Failed to send threat report to backend: {e}")

def log_traffic_to_backend(src_ip, request_path, request_method, action, rule_matched=None, status_code=200):
    try:
        # Avoid circular logging of telemetry endpoints
        if "/api/traffic" in request_path or "/api/events" in request_path or "/api/stats" in request_path or "/api/alerts" in request_path:
            return
            
        traffic_url = BACKEND_URL.replace('/alerts', '/traffic')
        payload = {
            "src_ip": src_ip,
            "request_path": request_path,
            "request_method": request_method,
            "action": action,
            "rule_matched": rule_matched,
            "status_code": status_code
        }
        requests.post(traffic_url, json=payload, timeout=2)
    except Exception as e:
        print(f"[Proxy Error] Failed to send traffic log to backend: {e}")

# HTML Custom Block Page for attackers
BLOCK_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACCESS DENIED | CloudShield Gateway</title>
    <style>
        body {
            background-color: #0B0F19;
            color: #EF4444;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            border: 2px solid #EF4444;
            border-radius: 12px;
            padding: 3rem;
            background-color: #111827;
            box-shadow: 0 0 30px rgba(239, 68, 68, 0.2);
            max-width: 500px;
        }
        .shield-icon {
            font-size: 5rem;
            margin-bottom: 1.5rem;
            animation: pulse 2s infinite;
        }
        h1 {
            margin: 0 0 1rem;
            font-size: 2.2rem;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        p {
            color: #9CA3AF;
            font-size: 1.1rem;
            line-height: 1.6;
            margin-bottom: 2rem;
        }
        .details {
            font-family: monospace;
            background-color: #1F2937;
            padding: 1rem;
            border-radius: 6px;
            color: #EF4444;
            text-align: left;
            font-size: 0.9rem;
        }
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
            100% { transform: scale(1); opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="shield-icon">🛡️⛔</div>
        <h1>Access Blocked</h1>
        <p>Your connection has been intercepted and blocked by the CloudShield Active Intrusion Prevention System (IPS).</p>
        <div class="details">
            <strong>REASON:</strong> {{ reason }}<br>
            <strong>IP ADDRESS:</strong> {{ ip }}<br>
            <strong>GATEWAY:</strong> CLOUDSHIELD-NODE-01<br>
            <strong>STATUS:</strong> BLOCKED & LOGGED
        </div>
    </div>
</body>
</html>
"""

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy_handler(path):
    src_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # 1. Check if the IP is dynamically blocked by the IDS
    if check_ip_banned(src_ip):
        log_traffic_to_backend(src_ip, request.path, request.method, "BLOCK", "IP_BANNED", 403)
        return render_template_string(BLOCK_PAGE, reason="IP Address Banned due to repeated malicious actions.", ip=src_ip), 403
    
    # 2. Fetch active custom rules policy configuration
    active_rules = get_active_rules()
    
    # 3. Compile request scopes
    payload_to_check = {
        "PATH": request.path,
        "QUERY": request.query_string.decode('utf-8', errors='ignore'),
        "BODY": request.get_data().decode('utf-8', errors='ignore'),
        "HEADERS": str(dict(request.headers))
    }
    
    # 4. Check dynamic signatures WAF rules
    for rule in active_rules:
        # Only evaluate if rule is enabled (value is 1 or True)
        if rule.get('enabled', 1):
            name = rule['rule_name']
            pattern_str = rule['pattern']
            target = rule['target_field']
            severity = rule.get('severity', 'HIGH')
            
            try:
                rx = re.compile(pattern_str)
            except Exception as e:
                print(f"[Proxy WAF] Failed to compile signature pattern for rule '{name}': {e}")
                continue
                
            # Determine content scope to check
            content_to_scan = []
            if target == 'QUERY_OR_BODY':
                content_to_scan = [payload_to_check['QUERY'], payload_to_check['BODY']]
            elif target == 'PATH':
                content_to_scan = [payload_to_check['PATH']]
            elif target == 'QUERY':
                content_to_scan = [payload_to_check['QUERY']]
            elif target == 'BODY':
                content_to_scan = [payload_to_check['BODY']]
            elif target == 'HEADERS':
                content_to_scan = [payload_to_check['HEADERS']]
                
            for content in content_to_scan:
                if content and rx.search(content):
                    description = f"Autonomous dynamic block: Rule [{name}] triggered in request field [{target}]."
                    report_threat(
                        src_ip=src_ip,
                        attack_type=name,
                        description=description,
                        severity=severity,
                        details={
                            "matched_signature": pattern_str,
                            "payload": content[:200]
                        }
                    )
                    log_traffic_to_backend(src_ip, request.path, request.method, "BLOCK", name, 403)
                    return render_template_string(BLOCK_PAGE, reason=f"Exploit attempt blocked: [{name}] signature matched.", ip=src_ip), 403
                
    # 5. Dynamic Honeypot Redirection (Deception Tech)
    path_lower = request.path.lower()
    is_decoy = False
    for decoy_path in DECOY_PATHS:
        if path_lower.startswith(decoy_path):
            is_decoy = True
            break
            
    # Select target destination
    target_base_url = HONEYPOT_URL if is_decoy else WEB_APP_URL
    target_url = f"{target_base_url}{request.full_path}"
    
    # Log deception redirect before executing
    if is_decoy:
        log_traffic_to_backend(src_ip, request.path, request.method, "DECEPTION", "Honeypot Decoy Redirect", 302)
    
    # 6. Proxy request to target
    try:
        headers = {key: value for key, value in request.headers if key.lower() not in ['host', 'content-length']}
        headers['X-Forwarded-For'] = src_ip
        
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=10
        )
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        resp_headers = [(name, value) for (name, value) in resp.headers.items() if name.lower() not in excluded_headers]
        
        if not is_decoy:
            log_traffic_to_backend(src_ip, request.path, request.method, "PASS", None, resp.status_code)
            
        return Response(resp.content, resp.status_code, resp_headers)
        
    except requests.exceptions.RequestException as e:
        print(f"[Proxy Error] Backend service connection failed: {e}")
        log_traffic_to_backend(src_ip, request.path, request.method, "BLOCK", "GATEWAY_ERROR", 502)
        return jsonify({"status": "error", "message": "Gateway error: Target host unreachable."}), 502

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
