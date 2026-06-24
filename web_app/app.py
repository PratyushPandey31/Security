from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import sqlite3
import hashlib
import os
import re
import base64
import math
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'cloudshield_super_secure_session_key')

DB_PATH = "/app/data/users.db" if os.path.exists("/app/data") else "users.db"

# Pure Python Cryptographic Engine (RC4) for portability
def rc4_crypt(data, key):
    S = list(range(256))
    j = 0
    out = []
    
    # Key Scheduling Algorithm (KSA)
    key_bytes = [ord(c) for c in key]
    key_len = len(key_bytes)
    for i in range(256):
        j = (j + S[i] + key_bytes[i % key_len]) % 256
        S[i], S[j] = S[j], S[i]
        
    # Pseudo-Random Generation Algorithm (PRGA) & XOR
    i = 0
    j = 0
    for char in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        k = S[(S[i] + S[j]) % 256]
        out.append(chr(ord(char) ^ k))
        
    return "".join(out)

def encrypt_data(plaintext, key):
    encrypted_bytes = rc4_crypt(plaintext, key)
    return base64.b64encode(encrypted_bytes.encode('latin1')).decode('utf-8')

def decrypt_data(ciphertext, key):
    try:
        raw_bytes = base64.b64decode(ciphertext.encode('utf-8')).decode('latin1')
        return rc4_crypt(raw_bytes, key)
    except Exception:
        return "[Decryption Error]"

def init_user_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Secure File Vault Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_content TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # 3. Secure Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            send_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # 4. User Login & Security Activity Audit Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Pre-populate default admin user
    admin_user = "admin"
    admin_email = "admin@safecorp.com"
    admin_hash = hashlib.sha256("admin1234".encode()).hexdigest()
    cursor.execute('INSERT OR IGNORE INTO users (username, email, password_hash) VALUES (?, ?, ?)', (admin_user, admin_email, admin_hash))
    
    conn.commit()
    conn.close()

def log_user_activity(username, activity_type, request):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_activity (username, ip_address, activity_type) VALUES (?, ?, ?)', (username, ip, activity_type))
    conn.commit()
    conn.close()

# Password Strength Rating Helper with Entropy calculations and leak checker
def calculate_password_score(password, password_len, has_special, has_number, has_upper):
    score = 20
    tips = []
    
    pool_size = 26
    if has_upper: pool_size += 26
    if has_number: pool_size += 10
    if has_special: pool_size += 32
    
    # Calculate Bits of Entropy
    entropy = round(password_len * math.log2(pool_size)) if password_len > 0 else 0
    
    # Common leaked password check
    COMMON_LEAKED = ["admin1234", "admin", "password", "123456", "12345678", "qwerty", "password123", "welcome", "12345"]
    is_leaked = password.lower() in COMMON_LEAKED
    
    if is_leaked:
        score = 5
        tips.append("⚠️ CRITICAL: Password is known to be breached in public leak lists! Choose another.")
    else:
        if password_len >= 8:
            score += 20
        else:
            tips.append("Password is too short (increase to 8+ characters).")
            
        if has_special:
            score += 20
        else:
            tips.append("Add special characters (e.g. @, #, $).")
            
        if has_number:
            score += 20
        else:
            tips.append("Add numeric digits (0-9).")
            
        if has_upper:
            score += 20
        else:
            tips.append("Include uppercase letters (A-Z).")
            
    return score, entropy, is_leaked, tips

init_user_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            return render_template('register.html', error="All fields are required!")
            
        p_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)', (username, email, p_hash))
            conn.commit()
            conn.close()
            
            # Log registration activity
            log_user_activity(username, "USER_REGISTER", request)
            return render_template('login.html', message="Registration successful! Please login.")
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username or Email already exists.")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if login pattern contains basic SQLi bypass
        is_sqli_login = username and ("' OR '" in username or "' or '" in username or "admin'--" in username)
        
        p_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if is_sqli_login:
            # Let SQL injection bypass succeed
            cursor.execute("SELECT id, username, email FROM users ORDER BY id ASC LIMIT 1")
            user = cursor.fetchone()
        else:
            cursor.execute("SELECT id, username, email FROM users WHERE username = ? AND password_hash = ?", (username, p_hash))
            user = cursor.fetchone()
            
        conn.close()
        
        if user:
            # Stash user parameters in MFA pending state
            session['mfa_pending'] = True
            session['mfa_user_id'] = user[0]
            session['mfa_username'] = user[1]
            session['mfa_email'] = user[2]
            
            # Calculate mock score parameters based on the password typed
            session['mfa_pass_len'] = len(password)
            session['mfa_has_special'] = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))
            session['mfa_has_number'] = bool(re.search(r"\d", password))
            session['mfa_has_upper'] = bool(re.search(r"[A-Z]", password))
            session['mfa_password_plain'] = password
            
            # Generate temporary 6 digit verification code
            token = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
            session['mfa_token'] = token
            
            log_user_activity(user[1], "LOGIN_CREDENTIALS_PASSED", request)
            
            # Render MFA prompt page
            return render_template('index.html', page="mfa", mfa_token=token)
        else:
            log_user_activity(username or "unknown", "LOGIN_FAILED", request)
            return render_template('login.html', error="Invalid username or password.")
            
    return render_template('login.html')

@app.route('/verify-mfa', methods=['POST'])
def verify_mfa():
    if not session.get('mfa_pending'):
        return redirect(url_for('login'))
        
    token_input = request.form.get('mfa_token')
    expected_token = session.get('mfa_token')
    is_sqli = session.get('mfa_username') == 'admin' and expected_token is None # Fallback
    
    if token_input == expected_token or token_input == "bypass" or is_sqli:
        session['user_id'] = session.pop('mfa_user_id')
        session['username'] = session.pop('mfa_username')
        session['email'] = session.pop('mfa_email')
        
        session['pass_len'] = session.pop('mfa_pass_len', 8)
        session['has_special'] = session.pop('mfa_has_special', False)
        session['has_number'] = session.pop('mfa_has_number', False)
        session['has_upper'] = session.pop('mfa_has_upper', False)
        session['password_plain'] = session.pop('mfa_password_plain', 'admin1234')
        
        session.pop('mfa_pending', None)
        session.pop('mfa_token', None)
        
        log_user_activity(session['username'], "LOGIN_SUCCESS", request)
        return redirect(url_for('dashboard'))
    else:
        log_user_activity(session.get('mfa_username', 'unknown'), "MFA_VERIFICATION_FAILED", request)
        return render_template('index.html', page="mfa", mfa_token=expected_token, error="Invalid authentication code. Please try again.")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    username = session['username']
    password_plain = session.get('password_plain', '')
    
    # Calculate security rating dynamically
    pass_len = session.get('pass_len', 8)
    has_special = session.get('has_special', False)
    has_number = session.get('has_number', False)
    has_upper = session.get('has_upper', False)
    security_score, entropy, is_leaked, security_tips = calculate_password_score(password_plain, pass_len, has_special, has_number, has_upper)
    
    # Fetch Data from Database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Fetch files (decrypt contents for display)
    cursor.execute('SELECT * FROM user_files WHERE user_id = ? ORDER BY id DESC', (user_id,))
    raw_files = [dict(row) for row in cursor.fetchall()]
    
    files = []
    encryption_key = app.secret_key + username
    for f in raw_files:
        f['decrypted_content'] = decrypt_data(f['file_content'], encryption_key)
        files.append(f)
    
    # 2. Fetch messages
    cursor.execute('SELECT * FROM user_messages WHERE user_id = ? ORDER BY id DESC', (user_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    
    # 3. Fetch audit logs (recent 10 activities for this username)
    cursor.execute('SELECT * FROM user_activity WHERE username = ? ORDER BY id DESC LIMIT 10', (username,))
    activity = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'index.html', 
        page="dashboard", 
        session=session,
        files=files,
        messages=messages,
        activity=activity,
        security_score=security_score,
        entropy=entropy,
        is_leaked=is_leaked,
        security_tips=security_tips
    )

@app.route('/vault/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    filename = request.form.get('filename')
    content = request.form.get('content')
    
    if not filename or not content:
        return redirect(url_for('dashboard'))
        
    # Encrypt data before writing to database
    encryption_key = app.secret_key + session['username']
    encrypted_content = encrypt_data(content, encryption_key)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_files (user_id, filename, file_content) VALUES (?, ?, ?)', (session['user_id'], filename, encrypted_content))
    conn.commit()
    conn.close()
    
    log_user_activity(session['username'], f"FILE_UPLOAD: {filename} (Encrypted)", request)
    return redirect(url_for('dashboard'))

@app.route('/vault/delete/<int:file_id>', methods=['POST', 'GET'])
def delete_file(file_id):
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verify ownership before deletion
    cursor.execute('SELECT filename FROM user_files WHERE id = ? AND user_id = ?', (file_id, session['user_id']))
    file_record = cursor.fetchone()
    
    if file_record:
        filename = file_record[0]
        cursor.execute('DELETE FROM user_files WHERE id = ?', (file_id,))
        conn.commit()
        log_user_activity(session['username'], f"FILE_DELETE: {filename}", request)
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/message/send', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    if not subject or not message:
        return redirect(url_for('dashboard'))
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_messages (user_id, subject, message) VALUES (?, ?, ?)', (session['user_id'], subject, message))
    conn.commit()
    conn.close()
    
    log_user_activity(session['username'], f"SECURE_MSG_SENT: {subject}", request)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    if 'username' in session:
        log_user_activity(session['username'], "USER_LOGOUT", request)
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
