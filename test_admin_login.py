import urllib.request
import urllib.parse
import http.cookiejar

url = "http://localhost:8080/login"
data = urllib.parse.urlencode({"username": "admin", "password": "admin1234"}).encode('utf-8')

# Enable Cookie management for session persistence
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")

try:
    print("[*] Testing admin login (admin/admin1234) with CookieJar...")
    with opener.open(req, timeout=3) as res:
        print(f"[+] Final Status Code: {res.status}")
        body = res.read().decode('utf-8', errors='ignore')
        print(f"[+] Final URL: {res.geturl()}")
        if "Profile Session" in body or "Welcome, admin" in body:
            print("[+] SUCCESS: Login completed, session cookie saved, and user dashboard loaded!")
        else:
            print("[-] FAILED: Dashboard did not load. Content check failed.")
except Exception as e:
    print(f"[!] Login failed: {e}")
