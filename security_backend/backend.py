from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
import time
import requests
import io
import csv
import urllib.parse
from datetime import datetime
import database

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize database
database.init_db()

sse_clients = []

# Traffic endpoints
@app.route('/api/traffic', methods=['POST'])
def receive_traffic():
    data = request.json or {}
    src_ip = data.get('src_ip')
    path = data.get('request_path')
    method = data.get('request_method')
    action = data.get('action', 'PASS')
    rule = data.get('rule_matched')
    status_code = data.get('status_code', 200)
    
    database.log_traffic(src_ip, path, method, action, rule, status_code)
    
    traffic_event = {
        "event_type": "traffic",
        "timestamp": datetime.now().isoformat(),
        "src_ip": src_ip,
        "request_path": path,
        "request_method": method,
        "action": action,
        "rule_matched": rule,
        "status_code": status_code
    }
    
    for q in sse_clients:
        q.append(traffic_event)
        
    return jsonify({"status": "success"})

@app.route('/api/traffic', methods=['GET'])
def get_traffic():
    limit = request.args.get('limit', 100, type=int)
    return jsonify(database.get_raw_traffic(limit))

# SSE Real-time alert feed stream
def event_stream():
    client_queue = []
    sse_clients.append(client_queue)
    last_ping = time.time()
    try:
        # Initial ping to establish connection
        yield "data: {\"type\": \"ping\"}\n\n"
        while True:
            if client_queue:
                event = client_queue.pop(0)
                yield f"data: {json.dumps(event)}\n\n"
            else:
                # Send periodic ping to detect disconnected clients and release the thread
                if time.time() - last_ping > 5:
                    yield "data: {\"type\": \"ping\"}\n\n"
                    last_ping = time.time()
                time.sleep(0.2)
    except (GeneratorExit, ConnectionError, BrokenPipeError):
        pass
    finally:
        if client_queue in sse_clients:
            sse_clients.remove(client_queue)

@app.route('/api/events')
def stream_events():
    return Response(event_stream(), mimetype="text/event-stream")

# Alert reporting
@app.route('/api/alerts', methods=['POST'])
def receive_alert():
    data = request.json
    src_ip = data.get('src_ip')
    attack_type = data.get('attack_type')
    request_path = data.get('request_path')
    request_method = data.get('request_method')
    severity = data.get('severity', 'LOW')
    description = data.get('description', '')
    details = data.get('details', '{}')
    
    database.add_alert(src_ip, attack_type, request_path, request_method, severity, description, details)
    
    is_banned = database.is_ip_banned(src_ip)
    alerts = database.get_all_alerts(limit=50)
    ip_alerts_count = sum(1 for a in alerts if a['src_ip'] == src_ip)
    
    ban_triggered = False
    if not is_banned:
        # Automate IP ban if 5 warnings or critical command injection detected
        if ip_alerts_count >= 5 or severity == 'CRITICAL':
            database.ban_ip(src_ip, f"Autonomous Firewall Ban: Malicious activity threshold exceeded ({ip_alerts_count} alerts).")
            is_banned = True
            ban_triggered = True
            
            # Broadcast IP ban event
            ban_alert = {
                "timestamp": datetime.now().isoformat(),
                "src_ip": src_ip,
                "attack_type": "IP Blocked",
                "request_path": request_path,
                "request_method": request_method,
                "severity": "CRITICAL",
                "description": f"Automated Dynamic Firewall blocked source IP: {src_ip}",
                "details": json.dumps({"reason": "Threat threshold crossed"}),
                "status": "BLOCKED"
            }
            for q in sse_clients:
                q.append(ban_alert)
                
    new_alert = {
        "timestamp": datetime.now().isoformat(),
        "src_ip": src_ip,
        "attack_type": attack_type,
        "request_path": request_path,
        "request_method": request_method,
        "severity": severity,
        "description": description,
        "details": details,
        "status": "BLOCKED" if is_banned else "LOGGED"
    }
    for q in sse_clients:
        q.append(new_alert)
        
    return jsonify({
        "status": "success",
        "banned": is_banned,
        "ban_triggered": ban_triggered
    })

# Fetch stats and alerts
@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(database.get_stats())

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    limit = request.args.get('limit', 100, type=int)
    return jsonify(database.get_all_alerts(limit))

@app.route('/api/banned-ips', methods=['GET'])
def get_banned():
    return jsonify(database.get_banned_ips())

@app.route('/api/unban', methods=['POST'])
def unban():
    ip = request.json.get('ip')
    if ip:
        database.unban_ip(ip)
        unban_event = {
            "timestamp": datetime.now().isoformat(),
            "src_ip": ip,
            "attack_type": "IP Unbanned",
            "request_path": "N/A",
            "request_method": "N/A",
            "severity": "INFO",
            "description": f"Admin manually unbanned IP: {ip}",
            "details": "{}",
            "status": "UNBANNED"
        }
        for q in sse_clients:
            q.append(unban_event)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/api/check-ban', methods=['GET'])
def check_ban():
    ip = request.args.get('ip')
    if ip:
        return jsonify({"banned": database.is_ip_banned(ip)})
    return jsonify({"status": "error"}), 400

# WAF Rules Endpoint
@app.route('/api/waf/rules', methods=['GET'])
def waf_rules():
    return jsonify(database.get_custom_rules())

@app.route('/api/waf/rules/toggle', methods=['POST'])
def toggle_waf_rule():
    data = request.json
    rule_name = data.get('rule_name')
    enabled = data.get('enabled')
    if rule_name is not None and enabled is not None:
        database.toggle_custom_rule(rule_name, enabled)
        
        # Broadcast configuration update alert
        rule_change = {
            "timestamp": datetime.now().isoformat(),
            "src_ip": "127.0.0.1",
            "attack_type": "WAF Policy Update",
            "request_path": "/api/waf/rules/toggle",
            "request_method": "POST",
            "severity": "INFO",
            "description": f"WAF Filter rule '{rule_name}' was toggled to: {'ENABLED' if enabled else 'DISABLED'}",
            "details": json.dumps({"rule": rule_name, "active": enabled}),
            "status": "CONFIG_UPDATE"
        }
        for q in sse_clients:
            q.append(rule_change)
            
        return jsonify({"status": "success", "rules": database.get_custom_rules()})
    return jsonify({"status": "error", "message": "Parameters missing."}), 400

@app.route('/api/waf/rules/add', methods=['POST'])
def add_waf_rule():
    data = request.json or {}
    name = data.get('rule_name')
    pattern = data.get('pattern')
    field = data.get('target_field', 'QUERY_OR_BODY')
    severity = data.get('severity', 'HIGH')
    
    if name and pattern:
        success = database.add_custom_rule(name, pattern, field, severity)
        if success:
            rule_add = {
                "timestamp": datetime.now().isoformat(),
                "src_ip": "127.0.0.1",
                "attack_type": "WAF Policy Update",
                "request_path": "/api/waf/rules/add",
                "request_method": "POST",
                "severity": "INFO",
                "description": f"New WAF custom signature rule added: '{name}' (Target: {field})",
                "details": json.dumps({"rule": name, "pattern": pattern, "target": field}),
                "status": "CONFIG_UPDATE"
            }
            for q in sse_clients:
                q.append(rule_add)
            return jsonify({"status": "success", "rules": database.get_custom_rules()})
    return jsonify({"status": "error", "message": "Failed to add WAF rule."}), 400

@app.route('/api/waf/rules/delete', methods=['POST'])
def delete_waf_rule():
    name = request.json.get('rule_name')
    if name:
        database.delete_custom_rule(name)
        rule_del = {
            "timestamp": datetime.now().isoformat(),
            "src_ip": "127.0.0.1",
            "attack_type": "WAF Policy Update",
            "request_path": "/api/waf/rules/delete",
            "request_method": "POST",
            "severity": "INFO",
            "description": f"WAF custom signature rule deleted: '{name}'",
            "details": json.dumps({"rule": name}),
            "status": "CONFIG_UPDATE"
        }
        for q in sse_clients:
            q.append(rule_del)
        return jsonify({"status": "success", "rules": database.get_custom_rules()})
    return jsonify({"status": "error"}), 400

# Log Exporter: Export logs as CSV
@app.route('/api/reports/csv')
def export_csv():
    alerts = database.get_all_alerts(limit=5000)
    
    siem_output = io.StringIO()
    writer = csv.writer(siem_output)
    
    # Headers
    writer.writerow(["Alert ID", "Timestamp", "Source IP", "Attack Type", "Path", "Method", "Severity", "Description", "Status"])
    
    for a in alerts:
        writer.writerow([
            a.get("id"),
            a.get("timestamp"),
            a.get("src_ip"),
            a.get("attack_type"),
            a.get("request_path"),
            a.get("request_method"),
            a.get("severity"),
            a.get("description"),
            a.get("status")
        ])
        
    response = Response(siem_output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=cloudshield_audit_log_{datetime.now().strftime('%Y%m%d')}.csv"
    return response

# Security Audit Scanner Engine
@app.route('/api/scanner/audit', methods=['POST'])
def run_vulnerability_scan():
    data = request.json or {}
    target_url = data.get('target_url', 'http://127.0.0.1:8080')
    
    print(f"[*] Starting Autonomous Security Audit Scanner on: {target_url}")
    
    findings = []
    grade_score = 100
    
    # Check 1: Directory Probing (Security Headers & Server Check)
    try:
        res = requests.get(target_url, timeout=3)
        headers = res.headers
        
        # Test HTTP Security Headers
        security_headers = {
            "X-Frame-Options": {
                "desc": "Clickjacking protection header is missing! Attackers can embed your site inside an iframe on malicious domains.",
                "impact": "User clickjacking attacks, credential harvesting, or fraudulent balance transfers via UI redressing.",
                "fix": "Configure your server response to return header: X-Frame-Options: SAMEORIGIN",
                "code": "# Flask implementation\n@app.after_request\ndef add_headers(response):\n    response.headers['X-Frame-Options'] = 'SAMEORIGIN'\n    return response\n\n# Nginx Configuration\nadd_header X-Frame-Options \"SAMEORIGIN\" always;"
            },
            "Content-Security-Policy": {
                "desc": "Content-Security-Policy (CSP) is missing! The browser does not restrict loaded content domains.",
                "impact": "Cross-Site Scripting (XSS), script injection, data theft, and clickjacking attacks.",
                "fix": "Return a custom Content-Security-Policy header outlining safe source locations.",
                "code": "# Flask implementation\nresponse.headers['Content-Security-Policy'] = \"default-src 'self';\"\n\n# Nginx Configuration\nadd_header Content-Security-Policy \"default-src 'self';\" always;"
            },
            "X-Content-Type-Options": {
                "desc": "X-Content-Type-Options sniffing protection is missing.",
                "impact": "MIME-sniffing exploits where non-executable files (e.g. images) are executed as Javascript.",
                "fix": "Add X-Content-Type-Options: nosniff header to responses.",
                "code": "# Flask implementation\nresponse.headers['X-Content-Type-Options'] = 'nosniff'\n\n# Nginx Configuration\nadd_header X-Content-Type-Options \"nosniff\" always;"
            },
            "Strict-Transport-Security": {
                "desc": "HTTP Strict Transport Security (HSTS) missing. Connection is vulnerable to man-in-the-middle downgrades.",
                "impact": "Attacker intercepts plain HTTP requests, downgrading SSL/TLS protection via SSLStrip tools.",
                "fix": "Add Strict-Transport-Security response header with a long max-age cache configuration.",
                "code": "# Flask implementation\nresponse.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'\n\n# Nginx Configuration\nadd_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;"
            }
        }
        
        for header, meta in security_headers.items():
            if header not in headers:
                findings.append({
                    "severity": "MEDIUM",
                    "title": f"Missing Header: {header}",
                    "details": meta["desc"],
                    "impact": meta["impact"],
                    "remediation": meta["fix"],
                    "code_snippet": meta["code"]
                })
                grade_score -= 8
            else:
                findings.append({
                    "severity": "SAFE",
                    "title": f"Header Security: {header} Active",
                    "details": f"The response contains the secure {header} header properly configured.",
                    "impact": "None. Exploit prevention is active.",
                    "remediation": "No action needed.",
                    "code_snippet": ""
                })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Could not establish target connection: {e}"
        }), 500
        
    # Check 2: Deception Honey paths scanning
    try:
        # Request honey path /admin
        honey_res = requests.get(f"{target_url}/admin", timeout=3)
        body = honey_res.text
        
        if "Internal Core Console" in body or "CORE CONTROL" in body:
            # Honeypot decoy did intercept successfully (Safe/Defense Active)
            findings.append({
                "severity": "SAFE",
                "title": "Active Deception Decoy Active",
                "details": "Automated probes searching for exposed administrative panels (/admin) are successfully redirected to the isolated Honeypot decoy sandbox.",
                "impact": "Zero impact. Attackers interact with isolated false variables while their footprints are logged.",
                "remediation": "No action needed. Honeypot decoy configuration is correct.",
                "code_snippet": ""
            })
        else:
            findings.append({
                "severity": "HIGH",
                "title": "Exposed Directory Probe Vulnerability",
                "details": "Admin paths are exposed directly to the public web without deception shielding, permitting brute force scanning.",
                "impact": "Attackers can target administration forms directly, bypass firewalls, or explore configurations.",
                "remediation": "Enable Deception Shield WAF proxy redirection for administrative endpoints.",
                "code_snippet": "# WAF Gateway Config (/proxy_waf/waf_proxy.py)\nDECOY_PATHS = [\"/admin\", \"/wp-admin\", \"/config\"]\nif any(request.path.startswith(dp) for dp in DECOY_PATHS):\n    return redirect_to_honeypot()"
            })
            grade_score -= 20
    except Exception as e:
        pass

    # Check 3: Active SQL Injection bypass test
    try:
        sqli_payload = "1' UNION SELECT username, password FROM users--"
        test_url = f"{target_url}/login"
        
        # Probe login with SQLi bypass payload
        sqli_res = requests.post(test_url, data={"username": sqli_payload, "password": "any"}, timeout=3)
        body = sqli_res.text
        
        # If body returns successful user login dashboard session, SQLi bypass succeeded (critical vulnerability!)
        if "Profile Session" in body or "Welcome" in body or "dashboard" in body or "MFA Verification" in body:
            findings.append({
                "severity": "CRITICAL",
                "title": "SQL Injection authentication Bypass Succeeded",
                "details": "Database is vulnerable to authentication bypass exploits using standard SQL Injection payloads. The input parameter is parsed dynamically.",
                "impact": "Full database leak. Attackers can read sensitive records, steal hashes, or drop files.",
                "remediation": "Turn ON WAF SQL Injection signatures or sanitize database login parameter parsing in code using placeholders.",
                "code_snippet": "# VULNERABLE CODE:\nquery = f\"SELECT * FROM users WHERE name = '{user}' AND pass = '{pwd}'\"\ncursor.execute(query) # Vulnerable to injection!\n\n# SECURE PARAMETERIZED CODE:\nquery = \"SELECT * FROM users WHERE name = ? AND pass = ?\"\ncursor.execute(query, (user, pwd)) # Protected against injection!"
            })
            grade_score -= 40
        else:
            findings.append({
                "severity": "SAFE",
                "title": "SQL Injection Shield Active",
                "details": "Database authentication bypass queries are successfully blocked and logged by the gateway IPS rules.",
                "impact": "None. Exploit prevention is active.",
                "remediation": "No action needed. Keep WAF SQL Injection signatures enabled.",
                "code_snippet": ""
            })
    except Exception as e:
        pass

    # Calculate final Grade
    grade = "F"
    if grade_score >= 90: grade = "A"
    elif grade_score >= 80: grade = "B"
    elif grade_score >= 70: grade = "C"
    elif grade_score >= 60: grade = "D"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "target_url": target_url,
        "grade_score": max(0, grade_score),
        "security_grade": grade,
        "total_probes": 6,
        "findings": findings
    }
    
    return jsonify(report)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
