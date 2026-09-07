from flask import Flask, render_template_string, request, jsonify, make_response, session, redirect
from flask_cors import CORS
from datetime import datetime
import hashlib
import os
import re
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
CORS(app)

# ============ SUPABASE CONFIGURATION ============
SUPABASE_URL = 'https://jcvisgkvwlzdohilimni.supabase.co'
SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpjdmlzZ2t2d2x6ZG9oaWxpbW5pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDcxNzE4MywiZXhwIjoyMTAwMjkzMTgzfQ.Fb5gcBleB_Xvv0bV0t2AF-o402nBNBz8qnFKkTUKGJk'

try:
    from supabase import create_client, Client
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    SUPABASE_AVAILABLE = True
    print("✅ Supabase client initialized")
except Exception as e:
    print(f"⚠️ Supabase client failed: {e}")
    SUPABASE_AVAILABLE = False
    supabase = None

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Trading Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 420px;
            width: 100%;
        }
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 10px; 
            font-size: 28px; 
        }
        .subtitle { 
            text-align: center; 
            color: #666; 
            margin-bottom: 30px; 
            font-size: 14px; 
        }
        .form-group { 
            margin-bottom: 20px; 
        }
        label { 
            display: block; 
            margin-bottom: 5px; 
            color: #333; 
            font-weight: 600; 
            font-size: 14px; 
        }
        input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        input:focus { 
            border-color: #667eea; 
            outline: none; 
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); 
        }
        .btn-login {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn-login:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3); 
        }
        .btn-login:disabled { 
            opacity: 0.6; 
            cursor: not-allowed; 
        }
        .alert {
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }
        .alert-success { 
            background: #d4edda; 
            color: #155724; 
            border: 1px solid #c3e6cb; 
            display: block; 
        }
        .alert-error { 
            background: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
            display: block; 
        }
        .alert-info { 
            background: #d1ecf1; 
            color: #0c5460; 
            border: 1px solid #bee5eb; 
            display: block; 
        }
        .register-link { 
            text-align: center; 
            margin-top: 20px; 
            color: #666; 
            font-size: 14px; 
        }
        .register-link a { 
            color: #667eea; 
            text-decoration: none; 
            font-weight: 600; 
        }
        .register-link a:hover { 
            text-decoration: underline; 
        }
        .remember-me {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 15px 0;
        }
        .remember-me input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .remember-me label {
            margin: 0;
            font-weight: normal;
            cursor: pointer;
        }
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 15px;
        }
        .status-online { background: #28a745; color: white; }
        .password-hint {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            cursor: pointer;
        }
        .password-hint:hover {
            color: #667eea;
        }
        .dashboard-link {
            text-align: center;
            margin-top: 10px;
        }
        .dashboard-link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            font-size: 13px;
        }
        .dashboard-link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Welcome Back</h1>
        <p class="subtitle">Login to your trading account</p>
        
        <div style="text-align: center; margin-bottom: 15px;">
            <span id="connectionStatus" class="status-badge status-online">✅ Server Ready</span>
        </div>
        
        <div id="alert" class="alert"></div>
        
        <form id="loginForm">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" placeholder="john@example.com" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required minlength="6">
                <div class="password-hint" onclick="togglePassword()">👁️ Show Password</div>
            </div>
            
            <div class="remember-me">
                <input type="checkbox" id="remember">
                <label for="remember">Remember me</label>
            </div>
            
            <button type="submit" class="btn-login" id="loginBtn">Login</button>
        </form>
        
        <div class="register-link">
            Don't have an account? <a href="#" onclick="goToRegister()">Register here</a>
        </div>
        

        
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 10px; border: 1px solid #e0e0e0;">
            <p style="font-size: 12px; color: #666; text-align: center; margin: 0;">
                💡 After registration, use your email and password to login.
            </p>
        </div>
    </div>

    <script>
        // ====== NAVIGATION ======
        function goToRegister() {
            window.location.href = 'http://localhost:5004';
        }

        
        // ====== TOGGLE PASSWORD ======
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                document.querySelector('.password-hint').textContent = '🙈 Hide Password';
            } else {
                passwordInput.type = 'password';
                document.querySelector('.password-hint').textContent = '👁️ Show Password';
            }
        }
        
        // ====== LOGIN FORM ======
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const btn = document.getElementById('loginBtn');
            const alertDiv = document.getElementById('alert');
            
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const remember = document.getElementById('remember').checked;
            
            if (!email || !password) {
                alertDiv.textContent = 'Please fill in all fields';
                alertDiv.className = 'alert alert-error';
                alertDiv.style.display = 'block';
                return;
            }
            
            btn.disabled = true;
            btn.textContent = 'Logging in...';
            alertDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: email,
                        password: password,
                        remember: remember
                    })
                });
                
                const result = await response.json();
                console.log('Login result:', result);
                
                if (result.success) {
                    alertDiv.innerHTML = `
                        <strong>✅ Login Successful!</strong><br>
                        Welcome back ${result.full_name}!
                    `;
                    alertDiv.className = 'alert alert-success';
                    alertDiv.style.display = 'block';
                    
                    btn.textContent = '✅ Redirecting...';
                    
                    setTimeout(() => {
                        window.location.href = 'http://localhost:5003';
                    }, 1500);
                    
                } else {
                    throw new Error(result.error || 'Login failed');
                }
            } catch (error) {
                console.error('Login error:', error);
                alertDiv.innerHTML = `
                    <strong>❌ Login Failed</strong><br>
                    ${error.message || 'Invalid email or password'}
                `;
                alertDiv.className = 'alert alert-error';
                alertDiv.style.display = 'block';
                btn.textContent = 'Login';
            } finally {
                btn.disabled = false;
            }
        });
        
        // ====== AUTO-FILL FROM COOKIES ======
        document.addEventListener('DOMContentLoaded', function() {
            const cookies = document.cookie.split(';').reduce((acc, cookie) => {
                const [key, value] = cookie.trim().split('=');
                if (key && value) acc[key] = decodeURIComponent(value);
                return acc;
            }, {});
            
            if (cookies.user_email) {
                document.getElementById('email').value = cookies.user_email;
                document.getElementById('remember').checked = true;
                document.getElementById('password').focus();
            }
        });
    </script>
</body>
</html>
"""

# ============ ROUTES ============

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/login')
def login_page():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        print(f"📝 Login attempt: {email}")
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user_data = None
        
        if SUPABASE_AVAILABLE and supabase:
            try:
                response = supabase.table('users')\
                    .select('*')\
                    .eq('email', email)\
                    .execute()
                if response.data and len(response.data) > 0:
                    user_data = response.data[0]
                    print(f"✅ User found in Supabase")
            except Exception as e:
                print(f"⚠️ Supabase query failed: {e}")
        
        if not user_data:
            return jsonify({'success': False, 'error': 'Account not found. Please register first.'}), 401
        
        stored_hash = user_data.get('password_hash', '')
        if stored_hash != password_hash:
            return jsonify({'success': False, 'error': 'Invalid password. Please try again.'}), 401
        
        if not user_data.get('is_active', False):
            return jsonify({'success': False, 'error': 'Account is not active. Please verify your email.'}), 401
        
        try:
            if SUPABASE_AVAILABLE and supabase:
                supabase.table('users')\
                    .update({'last_login': datetime.now().isoformat()})\
                    .eq('email', email)\
                    .execute()
        except:
            pass
        
        response = make_response(jsonify({
            'success': True,
            'user_id': user_data.get('id'),
            'email': email,
            'full_name': user_data.get('full_name', 'User'),
            'balance': user_data.get('trading_balance', 10000),
            'role': user_data.get('role', 'user')
        }))
        
        cookie_max_age = 30*24*60*60 if remember else 7*24*60*60
        response.set_cookie('user_id', str(user_data.get('id')), max_age=cookie_max_age, path='/')
        response.set_cookie('user_email', email, max_age=cookie_max_age, path='/')
        response.set_cookie('user_name', user_data.get('full_name', 'User'), max_age=cookie_max_age, path='/')
        response.set_cookie('user_role', user_data.get('role', 'user'), max_age=cookie_max_age, path='/')
        response.set_cookie('trading_balance', str(user_data.get('trading_balance', 10000)), max_age=cookie_max_age, path='/')
        response.set_cookie('is_active', 'true', max_age=cookie_max_age, path='/')
        response.set_cookie('logged_in', 'true', max_age=cookie_max_age, path='/')
        
        return response
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'success': True}))
    response.set_cookie('user_id', '', expires=0, path='/')
    response.set_cookie('user_email', '', expires=0, path='/')
    response.set_cookie('user_name', '', expires=0, path='/')
    response.set_cookie('user_role', '', expires=0, path='/')
    response.set_cookie('trading_balance', '', expires=0, path='/')
    response.set_cookie('is_active', '', expires=0, path='/')
    response.set_cookie('logged_in', '', expires=0, path='/')
    return response

# ============ MAIN ============

if __name__ == '__main__':
    print('\n' + '=' * 70)
    print('🔐 LOGIN PAGE')
    print('=' * 70)
    print('URL: http://localhost:5005')
    print('Register: http://localhost:5004')
    print('Dashboard: http://localhost:5003')
    print('=' * 70 + '\n')
    
    app.run(host='0.0.0.0', port=5005, debug=False)