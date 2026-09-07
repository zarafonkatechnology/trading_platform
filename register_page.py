
# UPDATE THESE WITH YOUR DETAILS
from flask import Flask, render_template_string, request, jsonify, make_response, session, redirect
from flask_cors import CORS
from datetime import datetime, timedelta
import hashlib
import os
import re
import random
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

# ============ EMAIL CONFIGURATION ============
EMAIL_SENDER = "zarafonkatechnology@gmail.com"  # CHANGE THIS - Your Gmail address
EMAIL_PASSWORD = "jfutbfbcnflakwvf"    # CHANGE THIS - Your app password (remove spaces)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# In-memory storage
memory_storage = {
    'users': {},
    'verification_codes': {}
}

# ============ EMAIL SENDER ============
def send_verification_email(to_email, full_name, code):
    """Send verification code via Gmail with SSL"""
    
    print("\n" + "=" * 70)
    print("📧 VERIFICATION CODE")
    print("=" * 70)
    print(f"To: {to_email}")
    print(f"Your verification code is: 🔑 {code}")
    print("=" * 70)
    print("")
    
    try:
        print(f"📤 Sending email to {to_email}...")
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = to_email
        msg['Subject'] = "🔐 Verify Your Trading Account"
        
        body = f"""
Hello {full_name},

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.

---
Trading Platform
"""
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Email failed: {e}")
        print(f"📱 Using CONSOLE MODE - Code: {code}")
        return True

# ============ HTML TEMPLATE ============
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - Trading Platform</title>
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
            max-width: 450px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
        }
        h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 28px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #333; font-weight: 600; font-size: 14px; }
        input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s;
        }
        input:focus { border-color: #667eea; outline: none; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .btn-register {
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
        .btn-register:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3); }
        .btn-register:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-verify {
            width: 100%;
            padding: 14px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn-verify:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(40, 167, 69, 0.3); }
        .btn-verify:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-resend {
            background: #ffc107;
            color: #333;
            border: none;
            padding: 8px 20px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-resend:hover { background: #e0a800; transform: scale(1.02); }
        .alert {
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; display: block; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; display: block; }
        .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; display: block; }
        .login-link { text-align: center; margin-top: 20px; color: #666; font-size: 14px; }
        .login-link a { color: #667eea; text-decoration: none; font-weight: 600; }
        .login-link a:hover { text-decoration: underline; }
        .password-hint { font-size: 12px; color: #666; margin-top: 5px; }
        .terms-container {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 12px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s;
        }
        .terms-container.active { border-color: #667eea; }
        .terms-header {
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        .terms-header input[type="checkbox"] {
            width: 18px;
            height: 18px;
            margin-top: 2px;
            flex-shrink: 0;
            cursor: pointer;
        }
        .terms-header label {
            font-weight: 600;
            color: #333;
            cursor: pointer;
            margin-bottom: 0;
            font-size: 14px;
        }
        .terms-header label span { color: #dc3545; }
        .terms-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.6s ease, padding 0.6s ease;
            padding: 0 10px;
            margin: 0;
        }
        .terms-content.open {
            max-height: 600px;
            overflow-y: auto;
            padding: 15px 10px 5px 10px;
            margin-top: 10px;
        }
        .terms-text { font-size: 13px; color: #444; line-height: 1.8; }
        .terms-text h4 { color: #333; margin: 15px 0 8px 0; font-size: 15px; font-weight: 700; }
        .terms-text h4:first-child { margin-top: 0; }
        .terms-text p { margin-bottom: 10px; }
        .terms-text ul { padding-left: 20px; margin-bottom: 12px; }
        .terms-text ul li { margin-bottom: 6px; }
        .read-more-btn {
            background: #667eea;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            padding: 10px 16px;
            margin-top: 10px;
            border-radius: 6px;
            transition: all 0.3s;
            width: 100%;
            text-align: center;
        }
        .read-more-btn:hover { background: #764ba2; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); }
        .verification-box {
            display: none;
            margin-top: 20px;
            padding: 25px;
            background: #fff3cd;
            border-radius: 10px;
            border: 2px solid #ffc107;
            text-align: center;
        }
        .verification-box h3 { color: #856404; margin-bottom: 15px; font-size: 20px; }
        .verification-box p { color: #856404; margin: 10px 0; }
        .verification-box .code-input {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 25px 0;
            flex-wrap: wrap;
        }
        .verification-box .code-input input {
            width: 50px;
            height: 60px;
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .verification-box .code-input input:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: #f8f9ff;
        }
        .success-box {
            display: none;
            margin-top: 20px;
            padding: 25px;
            background: #d4edda;
            border-radius: 10px;
            border: 2px solid #28a745;
            text-align: center;
        }
        .success-box h3 { color: #155724; margin-bottom: 10px; font-size: 22px; }
        .success-box p { color: #155724; margin: 10px 0; }
        .success-box .btn-group {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        .btn-login {
            background: #28a745;
            color: white;
            border: none;
            padding: 12px 35px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 15px;
        }
        .btn-login:hover { background: #218838; transform: scale(1.05); }
        .btn-register-another {
            background: #6c757d;
            color: white;
            border: none;
            padding: 12px 35px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 15px;
        }
        .btn-register-another:hover { background: #5a6268; transform: scale(1.05); }
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 15px;
        }
        .status-online { background: #28a745; color: white; }
        .timer { color: #dc3545; font-weight: bold; }
        .email-display { color: #667eea; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Create Account</h1>
        <p class="subtitle">Join our trading platform today</p>
        
        <div style="text-align: center; margin-bottom: 15px;">
            <span id="connectionStatus" class="status-badge status-online">✅ Server Ready</span>
        </div>
        
        <div id="alert" class="alert"></div>
        
        <!-- REGISTRATION FORM -->
        <form id="registerForm">
            <div class="form-group">
                <label for="fullName">Full Name *</label>
                <input type="text" id="fullName" name="full_name" placeholder="John Doe" required>
            </div>
            
            <div class="form-group">
                <label for="email">Email Address *</label>
                <input type="email" id="email" name="email" placeholder="john@example.com" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password *</label>
                <input type="password" id="password" name="password" placeholder="Min 6 characters" required minlength="6">
                <div class="password-hint">Must be at least 6 characters</div>
            </div>
            
            <div class="form-group">
                <label for="phone">Phone Number *</label>
                <input type="tel" id="phone" name="phone" placeholder="+1234567890" required>
            </div>
            
            <div class="form-group">
                <div class="terms-container" id="termsContainer">
                    <div class="terms-header">
                        <input type="checkbox" id="terms" required>
                        <label for="terms">I agree to the <strong>Terms & Conditions</strong> <span>*</span></label>
                    </div>
                    
                    <button type="button" class="read-more-btn" id="readMoreBtn">📖 Read Full Terms & Conditions</button>
                    
                    <div class="terms-content" id="termsContent">
                        <div class="terms-text">
                            <h4>1. ACCEPTANCE OF TERMS</h4>
                            <p>By registering an account and using our trading platform ("Platform"), you agree to be bound by these Terms and Conditions ("Terms").</p>
                            <h4>2. ELIGIBILITY AND ACCOUNT REGISTRATION</h4>
                            <p>You must be at least 18 years old to register. You agree to provide accurate information.</p>
                            <h4>3. TRADING AND INVESTMENT RISKS</h4>
                            <p><strong>RISK WARNING:</strong> Trading involves substantial risk. You may lose all your invested capital.</p>
                            <h4>4. SECURITY AND DATA PROTECTION</h4>
                            <p>We implement security measures to protect your data. You are responsible for your account security.</p>
                            <h4>5. PROHIBITED ACTIVITIES</h4>
                            <p>No market manipulation, fraud, money laundering, or unauthorized access.</p>
                            <h4>6. LIMITATION OF LIABILITY</h4>
                            <p>We are not liable for trading losses, system failures, or market volatility.</p>
                            <h4>7. GOVERNING LAW</h4>
                            <p>These terms are governed by applicable laws.</p>
                            <p style="margin-top: 20px; padding: 15px; background: #e8f0fe; border-radius: 8px; font-weight: 700; color: #1a3a6a; text-align: center; border: 2px solid #667eea;">
                                ⚠️ By checking the box above, you confirm that you have read and agree to these Terms & Conditions.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            
            <button type="submit" class="btn-register" id="registerBtn">Create Account</button>
            <div class="login-link">
            Already have an account? <a href="#" onclick="goToDashboard()">Go to Login Page</a>
        </div>
        </form>
        
        <!-- VERIFICATION BOX -->
        <div class="verification-box" id="verificationBox">
            <h3>🔐 Verify Your Email</h3>
            <p>We've sent a 6-digit verification code to <br><span class="email-display" id="verifyEmail">your@email.com</span></p>
            <p style="font-size: 14px; color: #856404;">Check your email inbox for the code.</p>
            
            <div class="code-input">
                <input type="text" maxlength="1" id="code1" oninput="moveNext(this, 'code2')" autofocus>
                <input type="text" maxlength="1" id="code2" oninput="moveNext(this, 'code3')">
                <input type="text" maxlength="1" id="code3" oninput="moveNext(this, 'code4')">
                <input type="text" maxlength="1" id="code4" oninput="moveNext(this, 'code5')">
                <input type="text" maxlength="1" id="code5" oninput="moveNext(this, 'code6')">
                <input type="text" maxlength="1" id="code6" oninput="moveNext(this, 'code6')">
            </div>
            
            <button class="btn-verify" id="verifyBtn" onclick="verifyCode()">✅ Verify Account</button>
            
            <div style="margin-top: 15px;">
                <span id="timerDisplay">Code expires in: <span class="timer" id="countdownTimer">10:00</span></span>
                <br><br>
                <button class="btn-resend" onclick="resendCode()">🔄 Resend Code</button>
            </div>
        </div>
        
        <!-- SUCCESS BOX -->
        <div class="success-box" id="successBox">
            <h3>✅ Registration Successful!</h3>
            <p id="successMessage" style="font-size: 16px; font-weight: 500;"></p>
            <p style="font-size: 14px; color: #155724; margin-top: 5px;">Your account has been created successfully.</p>
            <div class="btn-group">
                <button class="btn-login" onclick="goToDashboard()">🚀 Go to Login Page</button>
            </div>
        </div>
        

    </div>

    <script>
        let tempEmail = null;
        let tempFullName = null;
        let timerInterval = null;
        let timeLeft = 600;
        
        // ====== GO TO DASHBOARD (Port 5003) ======
        function goToDashboard() {
            window.location.href = 'http://localhost:5005';
        }
        
        // ====== TOGGLE TERMS ======
        document.getElementById('readMoreBtn').addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const termsContent = document.getElementById('termsContent');
            const termsContainer = document.getElementById('termsContainer');
            if (termsContent.classList.contains('open')) {
                termsContent.classList.remove('open');
                this.textContent = '📖 Read Full Terms & Conditions';
                this.style.background = '#667eea';
                termsContainer.classList.remove('active');
            } else {
                termsContent.classList.add('open');
                this.textContent = '📖 Read Less';
                this.style.background = '#764ba2';
                termsContainer.classList.add('active');
            }
        });
        
        // ====== MOVE TO NEXT INPUT ======
        function moveNext(current, nextId) {
            if (current.value.length >= 1) {
                const next = document.getElementById(nextId);
                if (next) next.focus();
            }
            const code1 = document.getElementById('code1').value;
            const code2 = document.getElementById('code2').value;
            const code3 = document.getElementById('code3').value;
            const code4 = document.getElementById('code4').value;
            const code5 = document.getElementById('code5').value;
            const code6 = document.getElementById('code6').value;
            if (code1 && code2 && code3 && code4 && code5 && code6) {
                verifyCode();
            }
        }
        
        // ====== START TIMER ======
        function startTimer() {
            timeLeft = 600;
            const timerDisplay = document.getElementById('countdownTimer');
            if (timerInterval) clearInterval(timerInterval);
            timerInterval = setInterval(() => {
                timeLeft--;
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
                if (timeLeft <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.textContent = '⏰ Expired!';
                    document.getElementById('verifyBtn').disabled = true;
                }
            }, 1000);
        }
        
        // ====== VERIFY CODE ======
        async function verifyCode() {
            const code = document.getElementById('code1').value +
                        document.getElementById('code2').value +
                        document.getElementById('code3').value +
                        document.getElementById('code4').value +
                        document.getElementById('code5').value +
                        document.getElementById('code6').value;
            
            if (code.length !== 6) {
                alert('Please enter all 6 digits');
                return;
            }
            
            const btn = document.getElementById('verifyBtn');
            btn.disabled = true;
            btn.textContent = 'Verifying...';
            
            try {
                const response = await fetch('/api/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: tempEmail,
                        code: code
                    })
                });
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('verificationBox').style.display = 'none';
                    document.getElementById('successBox').style.display = 'block';
                    document.getElementById('successMessage').textContent = `Welcome ${tempFullName}!`;
                    clearInterval(timerInterval);
                } else {
                    alert('❌ ' + (result.error || 'Invalid code.'));
                    ['code1', 'code2', 'code3', 'code4', 'code5', 'code6'].forEach(id => {
                        document.getElementById(id).value = '';
                    });
                    document.getElementById('code1').focus();
                }
            } catch (error) {
                alert('Error: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '✅ Verify Account';
            }
        }
        
        // ====== RESEND CODE ======
        async function resendCode() {
            try {
                const response = await fetch('/api/resend_code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: tempEmail,
                        full_name: tempFullName
                    })
                });
                const result = await response.json();
                if (result.success) {
                    alert('✅ New code sent! Check your email.');
                    startTimer();
                    document.getElementById('verifyBtn').disabled = false;
                    ['code1', 'code2', 'code3', 'code4', 'code5', 'code6'].forEach(id => {
                        document.getElementById(id).value = '';
                    });
                    document.getElementById('code1').focus();
                } else {
                    alert('❌ ' + (result.error || 'Error sending code'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
        
        // ====== REGISTER FORM ======
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const btn = document.getElementById('registerBtn');
            const alertDiv = document.getElementById('alert');
            
            const fullName = document.getElementById('fullName').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const phone = document.getElementById('phone').value.trim();
            const terms = document.getElementById('terms').checked;
            
            if (!terms) {
                alertDiv.textContent = 'Please agree to the Terms & Conditions';
                alertDiv.className = 'alert alert-error';
                alertDiv.style.display = 'block';
                return;
            }
            if (!fullName || !email || !password || !phone) {
                alertDiv.textContent = 'Please fill in all required fields';
                alertDiv.className = 'alert alert-error';
                alertDiv.style.display = 'block';
                return;
            }
            
            btn.disabled = true;
            btn.textContent = 'Sending Code...';
            alertDiv.style.display = 'none';
            
            try {
                const formData = new FormData(this);
                const response = await fetch('/api/send_verification', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.success) {
                    tempEmail = email;
                    tempFullName = fullName;
                    
                    document.getElementById('verifyEmail').textContent = email;
                    document.getElementById('verificationBox').style.display = 'block';
                    document.getElementById('registerForm').style.display = 'none';
                    
                    ['code1', 'code2', 'code3', 'code4', 'code5', 'code6'].forEach(id => {
                        document.getElementById(id).value = '';
                    });
                    document.getElementById('code1').focus();
                    
                    startTimer();
                    
                    alertDiv.innerHTML = `
                        <strong>📧 Check Your Email</strong><br>
                        Verification code sent to ${email}
                    `;
                    alertDiv.className = 'alert alert-info';
                    alertDiv.style.display = 'block';
                    
                    btn.textContent = '✅ Code Sent!';
                } else {
                    throw new Error(result.error || 'Failed to send code');
                }
            } catch (error) {
                console.error('Error:', error);
                alertDiv.innerHTML = `<strong>❌ Error</strong><br>${error.message || 'Failed to send verification code'}`;
                alertDiv.className = 'alert alert-error';
                alertDiv.style.display = 'block';
                btn.textContent = 'Create Account';
            } finally {
                btn.disabled = false;
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

@app.route('/api/send_verification', methods=['POST'])
def send_verification():
    """Send verification code WITHOUT creating user yet"""
    try:
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        
        print(f"\n📝 Registration request for: {email}")
        
        if not all([full_name, email, password, phone]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400
        
        # Check if user exists
        user_exists = False
        
        if SUPABASE_AVAILABLE and supabase:
            try:
                existing = supabase.table('users')\
                    .select('email')\
                    .eq('email', email)\
                    .execute()
                if existing and existing.data and len(existing.data) > 0:
                    user_exists = True
            except Exception as e:
                print(f"⚠️ Supabase check failed: {e}")
                if email in memory_storage['users']:
                    user_exists = True
        
        if user_exists:
            return jsonify({'success': False, 'error': 'Email already registered'}), 400
        
        # Generate user ID
        user_id = int(time.time() * 1000) + random.randint(1, 9999)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Store user data
        user_data = {
            'id': user_id,
            'email': email,
            'full_name': full_name,
            'phone': phone,
            'password_hash': password_hash,
            'leverage': 5,
            'role': 'user',
            'max_volume': 100,
            'max_positions': 10,
            'trading_balance': 10000.0,
            'trading_equity': 10000.0,
            'trading_profit': 0.0,
            'is_active': False,
            'is_verified': False,
            'email_verified': False,
            'phone_verified': False,
            'last_login': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Store in session and memory
        session[f'pending_user_{email}'] = {'user_data': user_data}
        memory_storage['users'][email] = user_data
        
        # Generate code
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        print(f"🔑 VERIFICATION CODE for {email}: {code}")
        print(f"⏰ Code expires in 10 minutes\n")
        
        memory_storage['verification_codes'][email] = {
            'code': code,
            'expires': datetime.now() + timedelta(minutes=10)
        }
        
        # Send code via email
        send_verification_email(email, full_name, code)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'email': email,
            'full_name': full_name,
            'message': 'Verification code sent'
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify', methods=['POST'])
def verify_code():
    """Verify the 6-digit code and create the user"""
    try:
        data = request.json
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return jsonify({'success': False, 'error': 'Email and code required'}), 400
        
        # Check code in memory
        stored = memory_storage['verification_codes'].get(email)
        if not stored:
            return jsonify({'success': False, 'error': 'No verification code found'}), 400
        
        if datetime.now() > stored['expires']:
            del memory_storage['verification_codes'][email]
            return jsonify({'success': False, 'error': 'Code expired'}), 400
        
        if stored['code'] != code:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400
        
        # Get user data
        user_data = memory_storage['users'].get(email)
        if not user_data:
            return jsonify({'success': False, 'error': 'User data not found'}), 400
        
        # Activate user
        user_data['is_active'] = True
        user_data['is_verified'] = True
        user_data['email_verified'] = True
        user_data['updated_at'] = datetime.now().isoformat()
        
        # Try to save to Supabase
        saved_to_supabase = False
        if SUPABASE_AVAILABLE and supabase:
            try:
                insert_response = supabase.table('users')\
                    .insert(user_data)\
                    .execute()
                if insert_response.data and len(insert_response.data) > 0:
                    saved_to_supabase = True
                    print(f"✅ User saved to Supabase: {email}")
            except Exception as e:
                print(f"⚠️ Could not save to Supabase: {e}")
                print(f"📱 User saved in memory only")
        
        # Clean up
        del memory_storage['verification_codes'][email]
        if email in session:
            del session[f'pending_user_{email}']
        
        # Set cookies
        response = make_response(jsonify({
            'success': True,
            'user_id': user_data['id'],
            'email': email,
            'full_name': user_data['full_name'],
            'balance': 10000,
            'saved_to_supabase': saved_to_supabase,
            'message': 'User verified and registered successfully'
        }))
        
        response.set_cookie('user_id', str(user_data['id']), max_age=7*24*60*60, path='/')
        response.set_cookie('user_email', email, max_age=7*24*60*60, path='/')
        response.set_cookie('user_name', user_data['full_name'], max_age=7*24*60*60, path='/')
        response.set_cookie('user_role', 'user', max_age=7*24*60*60, path='/')
        response.set_cookie('trading_balance', '10000', max_age=7*24*60*60, path='/')
        response.set_cookie('is_active', 'true', max_age=7*24*60*60, path='/')
        
        return response
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/resend_code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    try:
        data = request.json
        email = data.get('email')
        full_name = data.get('full_name', 'User')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email required'}), 400
        
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        print(f"🔑 NEW CODE for {email}: {code}")
        
        memory_storage['verification_codes'][email] = {
            'code': code,
            'expires': datetime.now() + timedelta(minutes=10)
        }
        
        send_verification_email(email, full_name, code)
        
        return jsonify({'success': True, 'message': 'New code sent'})
        
    except Exception as e:
        print(f"❌ Resend error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============ MAIN ============

if __name__ == '__main__':
    print('\n' + '=' * 70)
    print('📝 REGISTRATION PAGE')
    print('=' * 70)
    print('URL: http://localhost:5004')
    print('Dashboard: http://localhost:5003')
    print('After registration, click "Go to Dashboard"')
    print('=' * 70 + '\n')
    
    app.run(host='0.0.0.0', port=5004, debug=False)