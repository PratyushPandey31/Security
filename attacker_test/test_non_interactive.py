import urllib.request
import urllib.parse
import urllib.error
import json
import time

TARGET_URL = "http://localhost:8080"

def send_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    headers["User-Agent"] = "Mozilla/5.0 (CloudShield Automated Attacker v2.0)"
    
    req_data = None
    if data:
        if isinstance(data, dict):
            req_data = urllib.parse.urlencode(data).encode('utf-8')
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif isinstance(data, str):
            req_data = data.encode('utf-8')
            headers["Content-Type"] = "application/json"
            
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, response.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return 0, str(e)

def run():
    print("[*] Running Upgraded v2.0 Attack Pipeline...")
    
    # 1. Register a legitimate user
    reg_data = {"username": "aman123", "email": "aman@safecorp.com", "password": "safePassword!"}
    status, _ = send_request(TARGET_URL + "/register", method="POST", data=reg_data)
    print(f"[+] Step 1: Registered user 'aman123' (Status: {status})")
    
    # 2. Legitimate login
    login_data = {"username": "aman123", "password": "safePassword!"}
    status, _ = send_request(TARGET_URL + "/login", method="POST", data=login_data)
    print(f"[+] Step 2: Logged in legitimately as 'aman123' (Status: {status})")
    
    # 3. SQLi WAF Block
    sqli_url = TARGET_URL + "/index?search=" + urllib.parse.quote("1' UNION SELECT NULL--")
    status, _ = send_request(sqli_url)
    print(f"[+] Step 3: Sent WAF SQLi attack payload (Status: {status} - 403 means blocked)")
    
    # 4. XSS WAF Block
    xss_url = TARGET_URL + "/index?q=" + urllib.parse.quote("<script>alert(1)</script>")
    status, _ = send_request(xss_url)
    print(f"[+] Step 4: Sent WAF XSS attack payload (Status: {status} - 403 means blocked)")
    
    # 5. SQLi bypass login attempt
    sqli_login = {"username": "admin' OR '1'='1", "password": "any"}
    status, _ = send_request(TARGET_URL + "/login", method="POST", data=sqli_login)
    print(f"[+] Step 5: Attempted SQLi bypass login form (Status: {status} - 403 means blocked by WAF)")

    # 6. Access honeypot admin path
    status, _ = send_request(TARGET_URL + "/admin")
    print(f"[+] Step 6: Scanned decoy endpoint /admin (Status: {status} - silently redirected to honeypot)")
    
    # 7. Execute cmd in Honeypot to trigger dynamic ban
    status, _ = send_request(TARGET_URL + "/admin/execute", method="POST", data=json.dumps({"command": "id"}), headers={"Content-Type": "application/json"})
    print(f"[+] Step 7: Triggered Honeypot command execution (Status: {status})")
    
    # 8. Verify dynamic ban
    status, _ = send_request(TARGET_URL + "/")
    print(f"[+] Step 8: Checking gateway access after attack threshold (Status: {status} - 403 means dynamically banned!)")

if __name__ == "__main__":
    run()
