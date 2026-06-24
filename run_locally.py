import subprocess
import sys
import os
import time
import signal

processes = []

def install_dependencies():
    print("[*] Checking required Python dependencies...")
    try:
        import flask
        import requests
        print("[+] Dependencies are already installed.")
    except ImportError:
        print("[-] Dependencies missing. Installing 'flask' and 'requests'...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "requests"])
            print("[+] Installation successful!")
        except Exception as e:
            print(f"[!] Error installing dependencies: {e}")
            sys.exit(1)

def run_service(cmd, cwd, env_vars=None, service_name=""):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if env_vars:
        env.update(env_vars)
        
    p = subprocess.Popen(
        [sys.executable] + cmd,
        cwd=cwd,
        env=env,
        text=True
    )
    p.service_name = service_name
    processes.append(p)
    return p

def main():
    print("=" * 80)
    print("                CLOUDSHIELD LOCAL MULTI-SERVICE RUNNER                 ")
    print("=" * 80)
    print("[*] Starting CloudShield services natively using Python...")
    
    # 1. Install pip packages
    install_dependencies()
    
    # 2. Define service execution configurations
    services = [
        {
            "name": "Security Backend API",
            "cmd": ["backend.py"],
            "cwd": "security_backend",
            "env": {"PORT": "5000"}
        },
        {
            "name": "Legitimate Web Application",
            "cmd": ["app.py"],
            "cwd": "web_app",
            "env": {"PORT": "8000"}
        },
        {
            "name": "Deception Honeypot Decoy",
            "cmd": ["decoy.py"],
            "cwd": "honeypot_decoy",
            "env": {
                "PORT": "9000",
                "BACKEND_URL": "http://127.0.0.1:5000/api/alerts"
            }
        },
        {
            "name": "Proxy WAF Gateway",
            "cmd": ["waf_proxy.py"],
            "cwd": "proxy_waf",
            "env": {
                "PORT": "8080",
                "WEB_APP_URL": "http://127.0.0.1:8000",
                "HONEYPOT_URL": "http://127.0.0.1:9000",
                "BACKEND_URL": "http://127.0.0.1:5000/api/alerts"
            }
        },
        {
            "name": "SIEM Dashboard Server",
            "cmd": ["-m", "http.server", "8081"],
            "cwd": "security_dashboard",
            "env": {}
        }
    ]
    
    # 3. Spin up all components in background
    for s in services:
        print(f"[*] Launching {s['name']}...")
        run_service(s["cmd"], s["cwd"], s["env"], s["name"])
        time.sleep(1) # wait briefly before starting next service
        
    print("\n" + "=" * 80)
    print("[+] All services launched successfully!")
    print("    - Legitimate App:   http://localhost:8080  (via Proxy)")
    print("    - SIEM Dashboard:   http://localhost:8081")
    print("    - Security API:     http://localhost:5000")
    print("    - Honeypot Decoy:   Internal (Port 9000)")
    print("=" * 80)
    print("\n[!] PRESS CTRL+C TO STOP ALL SERVICES CLEANLY.\n")
    
    try:
        # Keep main thread alive and print logs
        while True:
            for p in processes:
                # Non-blocking poll
                if p.poll() is not None:
                    print(f"\n[!] Service '{p.service_name}' exited with code {p.returncode}. Stopping all...")
                    raise KeyboardInterrupt
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\n[*] Terminating all processes...")
        for p in processes:
            p.terminate()
            p.wait()
        print("[+] All services stopped successfully. Clean exit.")

if __name__ == "__main__":
    main()
