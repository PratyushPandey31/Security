import urllib.request
import urllib.error

try:
    print("[*] Requesting http://localhost:5000/api/waf/rules...")
    with urllib.request.urlopen("http://localhost:5000/api/waf/rules", timeout=3) as res:
        print(f"[+] Status: {res.status}")
        print(f"[+] Response: {res.read().decode('utf-8')}")
except Exception as e:
    print(f"[!] Rules endpoint failed: {e}")
