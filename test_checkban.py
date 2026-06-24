import urllib.request
import urllib.error

try:
    print("[*] Requesting http://localhost:5000/api/check-ban?ip=127.0.0.1...")
    with urllib.request.urlopen("http://localhost:5000/api/check-ban?ip=127.0.0.1", timeout=3) as res:
        print(f"[+] Status: {res.status}")
        print(f"[+] Response: {res.read().decode('utf-8')}")
except Exception as e:
    print(f"[!] Check-ban failed: {e}")
