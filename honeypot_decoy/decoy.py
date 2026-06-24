from flask import Flask, render_template, request, jsonify, redirect
import requests
import os
import json
from datetime import datetime

app = Flask(__name__)

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://security-backend:5000/api/alerts')

def log_to_backend(attack_type, description, severity, details=None):
    payload = {
        "src_ip": request.headers.get('X-Forwarded-For', request.remote_addr),
        "attack_type": attack_type,
        "request_path": request.path,
        "request_method": request.method,
        "severity": severity,
        "description": description,
        "details": json.dumps(details or {})
    }
    try:
        # Send event to the central security database
        requests.post(BACKEND_URL, json=payload, timeout=2)
    except Exception as e:
        print(f"[Honeypot Error] Failed to send alert to backend: {e}")

@app.route('/')
def index():
    # Honeypots often look like internal debug panels or administration logins
    log_to_backend(
        attack_type="Honeypot Discovery",
        description="User accessed honeypot entry page.",
        severity="MEDIUM",
        details={"user_agent": request.headers.get('User-Agent')}
    )
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Check if they are trying SQL injection in the honeypot
    is_sqli = "'" in username or "OR" in username.upper() or "UNION" in username.upper()
    
    log_to_backend(
        attack_type="Honeypot Brute Force" if not is_sqli else "Honeypot SQLi Attempt",
        description=f"Attempted login on honeypot decoy with username: '{username}'",
        severity="HIGH",
        details={
            "username": username,
            "password": password,
            "user_agent": request.headers.get('User-Agent')
        }
    )
    
    # Realistic delay to mimic database check
    import time
    time.sleep(0.5)
    
    # Always return failure to keep them trying, or let them log in to a "fake" admin dashboard to gather more telemetry
    if is_sqli:
        # SQLi mock login bypass success
        return render_template('login.html', error="SQL Injection Succeeded! Redirecting to admin session...", success=True)
    
    return render_template('login.html', error="Invalid administrative credentials. This attempt has been logged.")

@app.route('/admin/dashboard')
def dashboard():
    log_to_backend(
        attack_type="Honeypot Deep Access",
        description="Attacker attempted to access honeypot dashboard.",
        severity="CRITICAL",
        details={"query_params": dict(request.args)}
    )
    return jsonify({
        "status": "authorized",
        "system_status": "unstable",
        "debug_mode": True,
        "flag": "FLAG{DECEPTION_SUCCESSFUL_YOU_ARE_BEING_LOGGED}",
        "available_commands": ["ping", "whoami", "db_backup"]
    })

@app.route('/admin/execute', methods=['POST'])
def execute():
    cmd = request.json.get('command', '') if request.is_json else request.form.get('command', '')
    
    output = "Command not found."
    if "whoami" in cmd:
        output = "root"
    elif "id" in cmd:
        output = "uid=0(root) gid=0(root) groups=0(root)"
    elif "ls" in cmd:
        output = "config.py\ndatabase.db\nflag.txt\napp.py\nrequirements.txt"
    elif "cat" in cmd:
        output = "ACCESS DENIED: Kernel protection active."
    
    log_to_backend(
        attack_type="Honeypot Command Execution",
        description=f"Attacker tried executing shell command: '{cmd}'",
        severity="CRITICAL",
        details={"command": cmd, "output_returned": output}
    )
    
    return jsonify({"output": output})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port)
