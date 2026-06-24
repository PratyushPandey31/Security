import urllib.request
import urllib.error

try:
    print("[*] Requesting http://localhost:8000/...")
    with urllib.request.urlopen("http://localhost:8000/", timeout=3) as res:
        print(f"[+] Status: {res.status}")
        print(f"[+] Headers: {dict(res.headers)}")
        body = res.read().decode('utf-8', errors='ignore')
        print(f"[+] Body preview: {body[:150].strip()}...")
except Exception as e:
    print(f"[!] Legitimate App failed: {e}")
