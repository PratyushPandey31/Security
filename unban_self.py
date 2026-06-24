import urllib.request
import json

url = "http://localhost:5000/api/unban"
ips = ["127.0.0.1", "::1"]

for ip in ips:
    data = json.dumps({"ip": ip}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as res:
            print(f"[+] Successfully unbanned: {ip} (Response: {res.read().decode('utf-8')})")
    except Exception as e:
        print(f"[!] Failed to unban {ip}: {e}")
