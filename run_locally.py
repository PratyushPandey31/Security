import subprocess
import sys
import os
import time
import signal
import re

processes = []

def install_dependencies():
    print("[*] Checking required Python dependencies...")
    try:
        import flask
        import requests
        import flask_cors
        print("[+] Dependencies are already installed.")
    except ImportError:
        print("[-] Dependencies missing. Installing 'flask', 'requests', and 'flask-cors'...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "requests", "flask-cors"])
            print("[+] Installation successful!")
        except Exception as e:
            print(f"[!] Error installing dependencies: {e}")
            sys.exit(1)

def run_service(cmd, cwd, env_vars=None, service_name=""):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if env_vars:
        env.update(env_vars)
        
    is_python = cmd[0].endswith('.py') or cmd[0] == '-m'
    executable = [sys.executable] if is_python else []
    
    p = subprocess.Popen(
        executable + cmd,
        cwd=cwd,
        env=env,
        text=True,
        shell=not is_python
    )
    p.service_name = service_name
    processes.append(p)
    return p

def establish_tunnel():
    print("[*] Initializing secure HTTPS tunnel (localhost.run)...")
    # Launch localhost.run tunnel in background, piping output so we can parse it
    p = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:127.0.0.1:5000", "nokey@localhost.run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    tunnel_url = None
    start_time = time.time()
    
    # Read output to extract the random lhr.life tunnel URL
    while True:
        if time.time() - start_time > 20: # Timeout after 20 seconds
            print("[!] Tunnel establishment timed out.")
            break
            
        line = p.stdout.readline()
        if not line:
            break
            
        print(f"    [Tunnel] {line.strip()}")
        if "lhr.life" in line:
            match = re.search(r"https://[a-zA-Z0-9-]+\.lhr\.life", line)
            if match:
                tunnel_url = match.group(0)
                print(f"[+] Tunnel URL detected: {tunnel_url}")
                break
                
    if tunnel_url:
        # Save to tunnel_url.txt
        with open("tunnel_url.txt", "w") as f:
            f.write(tunnel_url)
            
        print("[*] Committing and pushing tunnel URL to GitHub...")
        try:
            # We run git commands synchronously to ensure it's pushed before dashboard accesses it
            subprocess.run(["git", "add", "tunnel_url.txt"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", f"Update active tunnel URL: {tunnel_url}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push", "origin", "main"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[+] Tunnel URL pushed successfully to GitHub!")
        except Exception as e:
            print(f"[!] Warning: Git push failed: {e}")
            
    # We must start a background thread/process to consume stdout so the tunnel process doesn't hang!
    import threading
    def consume_output(stream):
        try:
            for _ in stream:
                pass
        except Exception:
            pass
            
    t = threading.Thread(target=consume_output, args=(p.stdout,), daemon=True)
    t.start()
    
    p.service_name = "Secure HTTPS Tunnel (localhost.run)"
    processes.append(p)
    return p

def main():
    print("=" * 80)
    print("                CLOUDSHIELD LOCAL MULTI-SERVICE RUNNER                 ")
    print("=" * 80)
    print("[*] Starting CloudShield services natively using Python...")
    
    # 1. Install pip packages
    install_dependencies()
    
    # 2. Start SSH Tunnel and Push to GitHub
    establish_tunnel()
    
    # 3. Define other service execution configurations
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
    
    # 4. Spin up all components in background
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
