import urllib.request
import urllib.error

try:
    print("[*] Requesting http://localhost:8080/...")
    with urllib.request.urlopen("http://localhost:8080/", timeout=3) as res:
        print(f"[+] Status: {res.status}")
        print(f"[+] Headers: {dict(res.headers)}")
        body = res.read().decode('utf-8', errors='ignore')
        print(f"[+] Body length: {len(body)}")
        print(f"[+] Body preview: {body[:300].strip()}")
except urllib.error.HTTPError as e:
    print(f"[-] HTTP Error: {e.code} {e.reason}")
    print(f"[-] Response: {e.read().decode('utf-8', errors='ignore')[:300]}")
except Exception as e:
    print(f"[!] Connection failed: {e}")
