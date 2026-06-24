import os
import shutil

# Database paths
db_paths = [
    "security_backend/data/security.db",
    "security_backend/security.db",
    "web_app/data/users.db",
    "web_app/users.db"
]

print("[*] Resetting CloudShield databases to clean slate...")

for path in db_paths:
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"[+] Successfully deleted: {path}")
        except Exception as e:
            print(f"[!] Could not delete {path}: {e}")

# Also clean any data directory
data_dirs = ["security_backend/data", "web_app/data"]
for d in data_dirs:
    if os.path.exists(d):
        try:
            shutil.rmtree(d)
            print(f"[+] Cleaned data directory: {d}")
        except Exception as e:
            pass

print("[+] Database reset complete. Next startup will be completely fresh!")
