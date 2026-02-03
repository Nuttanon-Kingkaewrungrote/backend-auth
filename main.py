from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import pymysql
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
from pathlib import Path
import secrets
import uvicorn
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from starlette.responses import JSONResponse

# ============================================
# Load .env
# ============================================
env_path = Path('.') / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# ============================================
# Config
# ============================================
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-123')
ALGORITHM = 'HS256'

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fund_dashboard'),
}

# ============================================
# FastAPI App
# ============================================
app = FastAPI(title="Fund Dashboard Auth API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests. Please try again later."}
    )


app.add_middleware(SlowAPIASGIMiddleware)

# ============================================
# Database Connection
# ============================================
def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# ============================================
# Pydantic Models (ใช้สำหรับ Request Body)
# ============================================
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = ""

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class VerifyEmailRequest(BaseModel):
    token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    password: str
    confirm_text: str

# ============================================
# Helper: แกะ Token จาก Header
# ============================================
def get_token(authorization: Optional[str]):
    if not authorization:
        return None
    return authorization.replace("Bearer ", "")

def decode_token(token: str):
    """Decode token แล้วส่งกลับ payload หรือ None"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}

# ============================================
# 1. Home (Health Check)
# ============================================
@app.get("/")
def home():
    return {"message": "API is running!", "status": "OK"}

# ============================================
# 2. Register (สมัครสมาชิก)
# ============================================
@app.post("/api/auth/register")
def register(body: RegisterRequest):
    if not body.username or not body.password:
        return {"error": "Missing username or password"}

    hashed = bcrypt.hashpw(body.password.encode('utf-8'), bcrypt.gensalt())
    verification_token = secrets.token_urlsafe(32)

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, email, verification_token) VALUES (%s, %s, %s, %s)",
                (body.username, hashed.decode('utf-8'), body.email, verification_token)
            )
        conn.commit()
        conn.close()

        # TODO: ส่งอีเมล verify
        # verify_link = f"http://yoursite.com/verify-email?token={verification_token}"
        # send_email(body.email, verify_link)
        print(f"Verification token for {body.username}: {verification_token}")

        return {"message": "User created successfully. Please check your email to verify."}

    except pymysql.IntegrityError:
        return {"error": "Username already exists"}
    except Exception as e:
        return {"error": str(e)}

# ============================================
# 3. Login (เข้าสู่ระบบ)
# ============================================
@app.post("/api/auth/login")
def login(body: LoginRequest, request: Request):
    # Rate limit: 5 ครั้ง/นาที
    limiter.hit(request, "5/minute")

    if not body.username or not body.password:
        return {"error": "Missing credentials"}

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (body.username,))
            user = cur.fetchone()

        if user and bcrypt.checkpw(body.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # อัปเดท last_login
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()

            # กำหนดอายุ token
            token_expires = timedelta(days=30) if body.remember_me else timedelta(hours=24)

            # สร้าง JWT token
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + token_expires
            }, SECRET_KEY, algorithm=ALGORITHM)

            conn.close()
            return {
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "role": user['role']
                },
                "expires_in": 30 * 24 * 3600 if body.remember_me else 24 * 3600
            }

        conn.close()
        return {"error": "Invalid username or password"}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 4. Verify Token (ตรวจสอบ Token)
# ============================================
@app.get("/api/auth/verify")
def verify(authorization: Optional[str] = Header(default=None)):
    token = get_token(authorization)
    if not token:
        return {"error": "No token provided"}

    payload = decode_token(token)
    if "error" in payload:
        return payload

    return {"valid": True, "user": payload}

# ============================================
# 5. Logout (ออกจากระบบ)
# ============================================
@app.post("/api/auth/logout")
def logout():
    return {"message": "Logged out successfully"}

# ============================================
# 6. Forgot Password (ลืมรหัสผ่าน)
# ============================================
@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest):
    if not body.email:
        return {"error": "Email is required"}

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
            user = cur.fetchone()

        if user:
            reset_token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(hours=1)

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET reset_token = %s, reset_token_expires = %s WHERE email = %s",
                    (reset_token, expires, body.email)
                )
            conn.commit()

            # TODO: ส่งอีเมล reset
            # reset_link = f"http://yoursite.com/reset-password?token={reset_token}"
            # send_email(body.email, reset_link)
            print(f"Reset token for {body.email}: {reset_token}")

        conn.close()
        # ไม่บอกว่า email มีในระบบหรือไม่ (เพื่อความปลอดภัย)
        return {"message": "If the email exists, a password reset link has been sent"}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 7. Reset Password (ตั้งรหัสผ่านใหม่)
# ============================================
@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordRequest):
    if not body.token or not body.new_password:
        return {"error": "Token and new password are required"}

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE reset_token = %s AND reset_token_expires > NOW()",
                (body.token,)
            )
            user = cur.fetchone()

        if not user:
            conn.close()
            return {"error": "Invalid or expired token"}

        hashed = bcrypt.hashpw(body.new_password.encode('utf-8'), bcrypt.gensalt())

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s",
                (hashed.decode('utf-8'), user['id'])
            )
        conn.commit()
        conn.close()

        return {"message": "Password reset successfully"}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 8. Verify Email (ยืนยันอีเมล)
# ============================================
@app.post("/api/auth/verify-email")
def verify_email(body: VerifyEmailRequest):
    if not body.token:
        return {"error": "Token is required"}

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE verification_token = %s", (body.token,))
            user = cur.fetchone()

        if not user:
            conn.close()
            return {"error": "Invalid verification token"}

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET email_verified = TRUE, verification_token = NULL WHERE id = %s",
                (user['id'],)
            )
        conn.commit()
        conn.close()

        return {"message": "Email verified successfully"}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 9. Get Profile (ดึงข้อมูลผู้ใช้)
# ============================================
@app.get("/api/auth/profile")
def get_profile(authorization: Optional[str] = Header(default=None)):
    token = get_token(authorization)
    if not token:
        return {"error": "No token provided"}

    payload = decode_token(token)
    if "error" in payload:
        return payload

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, role, created_at, last_login FROM users WHERE id = %s",
                (payload['user_id'],)
            )
            user = cur.fetchone()
        conn.close()

        if user:
            return {
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "role": user['role'],
                    "created_at": str(user['created_at']),
                    "last_login": str(user['last_login']) if user['last_login'] else None
                }
            }
        return {"error": "User not found"}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 10. Refresh Token (ต่ออายุ Token)
# ============================================
@app.post("/api/auth/refresh")
def refresh_token(authorization: Optional[str] = Header(default=None)):
    token = get_token(authorization)
    if not token:
        return {"error": "No token provided"}

    try:
        # Decode โดยไม่เช็ค expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})

        # สร้าง token ใหม่ อายุ 24 ชั่วโมง
        new_token = jwt.encode({
            'user_id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY, algorithm=ALGORITHM)

        return {"token": new_token, "expires_in": 24 * 3600}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 11. Change Password (เปลี่ยนรหัสผ่าน)
# ============================================
@app.post("/api/auth/change-password")
def change_password(body: ChangePasswordRequest, authorization: Optional[str] = Header(default=None)):
    token = get_token(authorization)
    if not token:
        return {"error": "No token provided"}

    if not body.current_password or not body.new_password:
        return {"error": "Current password and new password are required"}

    if len(body.new_password) < 6:
        return {"error": "New password must be at least 6 characters"}

    if body.current_password == body.new_password:
        return {"error": "New password must be different from current password"}

    payload = decode_token(token)
    if "error" in payload:
        return payload

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (payload['user_id'],))
            user = cur.fetchone()

        if not user:
            conn.close()
            return {"error": "User not found"}

        # เช็ครหัสผ่านเก่า
        if not bcrypt.checkpw(body.current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            conn.close()
            return {"error": "Current password is incorrect"}

        # เข้ารหัสรหัสผ่านใหม่
        hashed = bcrypt.hashpw(body.new_password.encode('utf-8'), bcrypt.gensalt())

        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hashed.decode('utf-8'), payload['user_id']))
        conn.commit()
        conn.close()

        # TODO: ส่งอีเมลแจ้งเตือนว่ามีการเปลี่ยนรหัสผ่าน
        return {"message": "Password changed successfully"}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# 12. Delete Account (ลบบัญชี)
# ============================================
@app.delete("/api/auth/delete-account")
def delete_account(body: DeleteAccountRequest, authorization: Optional[str] = Header(default=None)):
    token = get_token(authorization)
    if not token:
        return {"error": "No token provided"}

    if not body.password:
        return {"error": "Password is required to delete account"}

    if body.confirm_text != "DELETE":
        return {"error": 'Please type "DELETE" to confirm account deletion'}

    payload = decode_token(token)
    if "error" in payload:
        return payload

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (payload['user_id'],))
            user = cur.fetchone()

        if not user:
            conn.close()
            return {"error": "User not found"}

        # เช็ครหัสผ่านก่อนลบ
        if not bcrypt.checkpw(body.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            conn.close()
            return {"error": "Incorrect password"}

        # ลบ user
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (payload['user_id'],))
        conn.commit()
        conn.close()

        return {"message": "Account deleted successfully", "username": user['username']}

    except Exception as e:
        return {"error": str(e)}

# ============================================
# Run Server
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 FastAPI Server Starting...")
    print("📍 URL:  http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
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
    print("   POST   /api/auth/change-password")
    print("   DELETE /api/auth/delete-account")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)