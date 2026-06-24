import urllib.request
import urllib.parse
import urllib.error
import json
import time

TARGET_URL = "http://localhost:8080"

def send_request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    headers["User-Agent"] = "Mozilla/5.0 (CloudShield Interactive Simulator)"
    
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

def main():
    print("=" * 80)
    print("           CLOUDSHIELD v2.0 INTERACTIVE DEMO SIMULATOR            ")
    print("=" * 80)
    
    # Step 1: User Registration
    input("\n[Press ENTER to simulate User Registration: /register]")
    reg_data = {"username": "aman123", "email": "aman@safecorp.com", "password": "safePassword!"}
    status, _ = send_request(TARGET_URL + "/register", method="POST", data=reg_data)
    print(f" [+] Status Code: {status}")
    print(" [*] User credentials stored in SQLite users.db.")
    
    # Step 2: Legitimate Login
    input("\n[Press ENTER to simulate Legitimate Login: /login]")
    login_data = {"username": "aman123", "password": "safePassword!"}
    status, body = send_request(TARGET_URL + "/login", method="POST", data=login_data)
    print(f" [+] Status Code: {status}")
    if "Profile Session" in body or "Welcome" in body or status == 302 or status == 200:
        print(" [+] Authenticated Session Granted! User Dashboard is accessible.")
        
    # Step 3: SQL Injection Bypass Attempt
    input("\n[Press ENTER to simulate SQL Injection bypass on login form: ' OR '1'='1]")
    sqli_login = {"username": "admin' OR '1'='1", "password": "any"}
    status, body = send_request(TARGET_URL + "/login", method="POST", data=sqli_login)
    print(f" [+] Status Code: {status}")
    if "Access Blocked" in body or status == 403:
        print(" [*] BLOCKED! Proxy WAF intercepted SQL Injection pattern. Alert sent to SIEM.")
    else:
        print(" [!] WARNING: Bypass succeeded (This means SQLi protection was toggled OFF in SIEM).")

    # Step 4: Honeypot scan and dynamic ban
    input("\n[Press ENTER to scan admin paths & execute shell command inside Honeypot decoy]")
    print(">>> Accessing /admin...")
    send_request(TARGET_URL + "/admin")
    print(">>> Executing command: id...")
    status, body = send_request(TARGET_URL + "/admin/execute", method="POST", data=json.dumps({"command": "id"}), headers={"Content-Type": "application/json"})
    print(f" [+] Status Code: {status}")
    
    # Step 5: Test IP block
    input("\n[Press ENTER to check gateway access status after triggering dynamic block]")
    status, body = send_request(TARGET_URL + "/")
    print(f" [+] Status Code: {status}")
    if status == 403:
        print(" [x] SUCCESS: Source IP is actively blocked by the WAF Firewall.")
        print("     Visit http://localhost:8081, login (admin/admin1234), and click 'Unban IP' to restore access.")
    else:
        print(" [!] Warning: Connection allowed. Ban not triggered.")
        
    print("\n" + "=" * 80)
    print(" DEMO PIPELINE COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
