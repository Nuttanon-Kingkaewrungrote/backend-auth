from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
from pathlib import Path


app = Flask(__name__)
CORS(app) 
app.config['SECRET_KEY'] = 'your-secret-key-123'

env_path = Path('.') / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': os.getenv('DB_PASSWORD'),
    'database': 'fund_dashboard'
}

def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


# Home & Health Check

@app.route('/')
def home():
    return jsonify({'message': 'API is running!', 'status': 'OK'})



# Register (สมัครสมาชิก)

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email', '')
    
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # สร้าง verification token
    verification_token = secrets.token_urlsafe(32)
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, verification_token) VALUES (%s, %s, %s, %s)",
                (username, hashed.decode('utf-8'), email, verification_token)
            )
        conn.commit()
        conn.close()
        
        # TODO: ส่งอีเมล verify
        # verify_link = f"http://yoursite.com/verify-email?token={verification_token}"
        # send_email(email, verify_link)
        
        print(f"Verification token for {username}: {verification_token}")  # ดูใน console
        
        return jsonify({
            'message': 'User created successfully. Please check your email to verify.'
        }), 201
    except pymysql.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Login (เข้าสู่ระบบ)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    remember_me = data.get('remember_me', False)
    
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()
            
            # ปรับอายุ token ตาม remember_me
            if remember_me:
                token_expires = timedelta(days=30)  # จำ 30 วัน
            else:
                token_expires = timedelta(hours=24)  # 24 ชม.
            
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + token_expires
            }, app.config['SECRET_KEY'], algorithm='HS256')
            
            conn.close()
            return jsonify({
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role']
                },
                'expires_in': 30 * 24 * 3600 if remember_me else 24 * 3600
            }), 200
        
        conn.close()
        return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Verify Token (ตรวจสอบ Token)

@app.route('/api/auth/verify', methods=['GET'])
def verify():
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return jsonify({'valid': True, 'user': payload}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401



# Logout (ออกจากระบบ)

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logged out successfully'}), 200



# Forgot Password (ลืมรหัสผ่าน)

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        
        if user:
            # สร้าง reset token
            reset_token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(hours=1)  # Token หมดอายุ 1 ชม.
            
            # บันทึก token ลง database
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE email = %s",
                    (reset_token, expires, email)
                )
            conn.commit()
            
            # TODO: ส่งอีเมล
            # reset_link = f"http://yoursite.com/reset-password?token={reset_token}"
            # send_email(email, reset_link)
            
            print(f"Reset token for {email}: {reset_token}")  # ดูใน console
        
        conn.close()
        
        # เพื่อความปลอดภัย ไม่บอกว่า email มีหรือไม่มีในระบบ
        return jsonify({
            'message': 'If the email exists, a password reset link has been sent'
        }), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Reset Password (ตั้งรหัสผ่านใหม่)

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({'error': 'Token and new password are required'}), 400
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            # หา user ด้วย token และเช็คว่ายังไม่หมดอายุ
            cursor.execute(
                "SELECT * FROM users WHERE reset_token = %s AND reset_token_expires > NOW()",
                (token,)
            )
            user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        # เข้ารหัสรหัสผ่านใหม่
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # อัพเดทรหัสผ่านและลบ token
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s",
                (hashed.decode('utf-8'), user['id'])
            )
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Password reset successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Verify Email (ยืนยันอีเมล)

@app.route('/api/auth/verify-email', methods=['POST'])
def verify_email():
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 400
    
    try:
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE verification_token = %s",
                (token,)
            )
            user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'Invalid verification token'}), 400
        
        # อัพเดทสถานะเป็นยืนยันแล้ว
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET email_verified = TRUE, verification_token = NULL WHERE id = %s",
                (user['id'],)
            )
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Email verified successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Get Profile (ดึงข้อมูลผู้ใช้)

@app.route('/api/auth/profile', methods=['GET'])
def get_profile():
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['user_id']
        
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, role, created_at, last_login FROM users WHERE id = %s", 
                (user_id,)
            )
            user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return jsonify({
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role'],
                    'created_at': str(user['created_at']),
                    'last_login': str(user['last_login']) if user['last_login'] else None
                }
            }), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Refresh Token (ต่ออายุ Token)

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        # Decode โดยไม่ verify expiration
        payload = jwt.decode(
            token, 
            app.config['SECRET_KEY'], 
            algorithms=['HS256'],
            options={"verify_exp": False}
        )
        
        # สร้าง token ใหม่
        new_token = jwt.encode({
            'user_id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': new_token,
            'expires_in': 24 * 3600
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 401



# Change Password (เปลี่ยนรหัสผ่าน) ⭐ ใหม่

@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """
    เปลี่ยนรหัสผ่าน (ต้อง login อยู่)
    
    Request Body:
    {
        "current_password": "รหัสผ่านเก่า",
        "new_password": "รหัสผ่านใหม่"
    }
    
    Headers:
    Authorization: Bearer <token>
    """
    # ดึง token จาก header
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    # ดึงข้อมูลจาก request body
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    # Validate input
    if not current_password or not new_password:
        return jsonify({'error': 'Current password and new password are required'}), 400
    
    # เช็ค password ใหม่ว่ายาวพอไหม
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    # เช็คว่า password ใหม่ต้องไม่เหมือนเก่า
    if current_password == new_password:
        return jsonify({'error': 'New password must be different from current password'}), 400
    
    try:
        # Decode token เพื่อหา user_id
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['user_id']
        
        # ดึงข้อมูล user จาก database
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # เช็ครหัสผ่านเก่าว่าถูกต้องไหม
        if not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # เข้ารหัสรหัสผ่านใหม่
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # อัพเดทรหัสผ่านในฐานข้อมูล
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed.decode('utf-8'), user_id)
            )
        conn.commit()
        conn.close()
        
        # TODO: ส่งอีเมลแจ้งเตือนว่ามีการเปลี่ยนรหัสผ่าน
        # send_email(user['email'], "Password Changed", "Your password has been changed")
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Delete Account (ลบบัญชี) ⭐ ใหม่

@app.route('/api/auth/delete-account', methods=['DELETE'])
def delete_account():
    """
    ลบบัญชีผู้ใช้ (ต้อง login อยู่)
    
    Request Body:
    {
        "password": "รหัสผ่านเพื่อยืนยัน",
        "confirm_text": "DELETE"
    }
    
    Headers:
    Authorization: Bearer <token>
    """
    # ดึง token จาก header
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    # ดึงข้อมูลจาก request body
    data = request.json
    password = data.get('password')
    confirm_text = data.get('confirm_text')
    
    # Validate input
    if not password:
        return jsonify({'error': 'Password is required to delete account'}), 400
    
    # ต้องพิมพ์คำว่า "DELETE" เพื่อยืนยัน
    if confirm_text != 'DELETE':
        return jsonify({'error': 'Please type "DELETE" to confirm account deletion'}), 400
    
    try:
        # Decode token เพื่อหา user_id
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['user_id']
        
        # ดึงข้อมูล user จาก database
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # เช็ครหัสผ่านว่าถูกต้องไหม
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            conn.close()
            return jsonify({'error': 'Incorrect password'}), 401
        
        # ลบ user จากฐานข้อมูล
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Account deleted successfully',
            'username': user['username']
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Run Server

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Flask API Server Starting...")
    print("📍 URL: http://localhost:5000")
    print("=" * 50)
    print("\n✨ Available Endpoints:")
    print("   POST   /api/auth/register")
    print("   POST   /api/auth/login")
    print("   GET    /api/auth/verify")
    print("   POST   /api/auth/logout")
    print("   POST   /api/auth/forgot-password")
    print("   POST   /api/auth/reset-password")
    print("   POST   /api/auth/verify-email")
    print("   GET    /api/auth/profile")
    print("   POST   /api/auth/refresh")
    print("   POST   /api/auth/change-password")      # ⭐ เพิ่ม
    print("   DELETE /api/auth/delete-account")       # ⭐ เพิ่ม
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)