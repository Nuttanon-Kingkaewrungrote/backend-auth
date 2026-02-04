from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import pymysql
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
import secrets
import uvicorn
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from starlette.responses import JSONResponse
import logging
from dotenv import load_dotenv

# ============================================
# Load .env
# ============================================
load_dotenv()

# ============================================
# Setup Logging
# ============================================
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
app = FastAPI(
    title="Fund Dashboard Auth API",
    version="1.0.0",
    description="REST API for Authentication with JWT"
)

# ============================================
# Security Scheme
# ============================================
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency สำหรับตรวจสอบ token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ============================================
# Middleware
# ============================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ใน production ควรระบุ domain ชัดเจน
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded from IP: {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests. Please try again later."}
    )

app.add_middleware(SlowAPIASGIMiddleware)

# ============================================
# Database Connection
# ============================================
def get_db():
    """สร้าง database connection"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# ============================================
# Pydantic Models
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
# Health Check Endpoints
# ============================================
@app.get("/")
def home():
    """Root endpoint - API status"""
    return {
        "message": "Fund Dashboard Auth API",
        "status": "OK",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    """Health check endpoint สำหรับ monitoring"""
    db_status = "unknown"
    
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")
    
    status_code = "ok" if db_status == "healthy" else "degraded"
    
    return {
        "status": status_code,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "healthy",
            "database": db_status
        }
    }

# ============================================
# Authentication Endpoints
# ============================================

@app.post("/api/auth/register", tags=["Authentication"])
def register(body: RegisterRequest):
    """สมัครสมาชิก - Register new user"""
    if not body.username or not body.password:
        logger.warning("Register attempt with missing credentials")
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

        logger.info(f"New user registered: {body.username}")
        print(f"Verification token for {body.username}: {verification_token}")
        
        # TODO: Send verification email
        # send_verification_email(body.email, verification_token)
        
        return {"message": "User created successfully. Please check your email to verify."}

    except pymysql.IntegrityError:
        logger.warning(f"Register failed: Username '{body.username}' already exists")
        return {"error": "Username already exists"}
    except Exception as e:
        logger.error(f"Register error: {e}")
        return {"error": str(e)}

@app.post("/api/auth/login", tags=["Authentication"])
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    """เข้าสู่ระบบ - User login"""
    logger.info(f"Login attempt for user: {body.username} from IP: {request.client.host}")
    
    if not body.username or not body.password:
        return {"error": "Missing credentials"}

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (body.username,))
            user = cur.fetchone()

        if user and bcrypt.checkpw(body.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Update last login
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()

            # Create JWT token
            token_expires = timedelta(days=30) if body.remember_me else timedelta(hours=24)
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + token_expires
            }, SECRET_KEY, algorithm=ALGORITHM)

            conn.close()
            
            logger.info(f"Login successful for user: {body.username}")
            
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
        logger.warning(f"Login failed for user: {body.username} - Invalid credentials")
        return {"error": "Invalid username or password"}

    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"error": str(e)}

@app.get("/api/auth/verify", tags=["Authentication"])
def verify(user: dict = Depends(get_current_user)):
    """ตรวจสอบ Token - Verify JWT token"""
    return {"valid": True, "user": user}

@app.post("/api/auth/logout", tags=["Authentication"])
def logout():
    """ออกจากระบบ - User logout"""
    return {"message": "Logged out successfully"}

@app.post("/api/auth/forgot-password", tags=["Authentication"])
def forgot_password(body: ForgotPasswordRequest):
    """ลืมรหัสผ่าน - Request password reset"""
    logger.info(f"Password reset requested for email: {body.email}")
    
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
            
            logger.info(f"Password reset token generated for: {body.email}")
            print(f"Reset token for {body.email}: {reset_token}")
            
            # TODO: Send reset email
            # send_password_reset_email(body.email, reset_token)

        conn.close()
        return {"message": "If the email exists, a password reset link has been sent"}

    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return {"error": str(e)}

@app.post("/api/auth/reset-password", tags=["Authentication"])
def reset_password(body: ResetPasswordRequest):
    """รีเซ็ตรหัสผ่าน - Reset password with token"""
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
            logger.warning("Password reset failed: Invalid or expired token")
            return {"error": "Invalid or expired token"}

        hashed = bcrypt.hashpw(body.new_password.encode('utf-8'), bcrypt.gensalt())

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL WHERE id = %s",
                (hashed.decode('utf-8'), user['id'])
            )
        conn.commit()
        conn.close()

        logger.info(f"Password reset successful for user ID: {user['id']}")
        return {"message": "Password reset successfully"}

    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return {"error": str(e)}

@app.post("/api/auth/verify-email", tags=["Authentication"])
def verify_email(body: VerifyEmailRequest):
    """ยืนยันอีเมล - Verify email with token"""
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

        logger.info(f"Email verified for user: {user['username']}")
        return {"message": "Email verified successfully"}

    except Exception as e:
        logger.error(f"Verify email error: {e}")
        return {"error": str(e)}

# ============================================
# User Management Endpoints
# ============================================

@app.get("/api/auth/profile", tags=["User Management"])
def get_profile(user: dict = Depends(get_current_user)):
    """ดูข้อมูลผู้ใช้ - Get user profile"""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, role, created_at, last_login FROM users WHERE id = %s",
                (user['user_id'],)
            )
            user_data = cur.fetchone()
        conn.close()

        if user_data:
            return {
                "user": {
                    "id": user_data['id'],
                    "username": user_data['username'],
                    "email": user_data['email'],
                    "role": user_data['role'],
                    "created_at": str(user_data['created_at']),
                    "last_login": str(user_data['last_login']) if user_data['last_login'] else None
                }
            }
        raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/refresh", tags=["User Management"])
def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """ต่ออายุ Token - Refresh access token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # Decode without expiration check
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})

        # Create new token
        new_token = jwt.encode({
            'user_id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, SECRET_KEY, algorithm=ALGORITHM)

        logger.info(f"Token refreshed for user: {payload['username']}")
        return {"token": new_token, "expires_in": 24 * 3600}

    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/change-password", tags=["User Management"])
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """เปลี่ยนรหัสผ่าน - Change user password"""
    if not body.current_password or not body.new_password:
        raise HTTPException(status_code=400, detail="Current password and new password are required")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user['user_id'],))
            user_data = cur.fetchone()

        if not user_data:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not bcrypt.checkpw(body.current_password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
            conn.close()
            logger.warning(f"Change password failed for user {user['username']}: Incorrect current password")
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Hash new password
        hashed = bcrypt.hashpw(body.new_password.encode('utf-8'), bcrypt.gensalt())

        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hashed.decode('utf-8'), user['user_id']))
        conn.commit()
        conn.close()

        logger.info(f"Password changed successfully for user: {user['username']}")
        
        # TODO: Send email notification
        # send_password_changed_email(user_data['email'])
        
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/auth/delete-account", tags=["User Management"])
def delete_account(body: DeleteAccountRequest, user: dict = Depends(get_current_user)):
    """ลบบัญชี - Delete user account"""
    if not body.password:
        raise HTTPException(status_code=400, detail="Password is required to delete account")

    if body.confirm_text != "DELETE":
        raise HTTPException(status_code=400, detail='Please type "DELETE" to confirm account deletion')

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user['user_id'],))
            user_data = cur.fetchone()

        if not user_data:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        # Verify password
        if not bcrypt.checkpw(body.password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
            conn.close()
            logger.warning(f"Delete account failed for user {user['username']}: Incorrect password")
            raise HTTPException(status_code=400, detail="Incorrect password")

        # Delete user
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user['user_id'],))
        conn.commit()
        conn.close()

        logger.info(f"Account deleted: {user_data['username']}")
        return {"message": "Account deleted successfully", "username": user_data['username']}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# Run Server
# ============================================
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 FastAPI Server Starting...")
    logger.info("📍 URL:  http://localhost:8000")
    logger.info("📖 Docs: http://localhost:8000/docs")
    logger.info("=" * 50)
    logger.info("\n✨ Available Endpoints:")
    logger.info("   GET    /                             - API Info")
    logger.info("   GET    /health                       - Health Check")
    logger.info("   POST   /api/auth/register            - Register")
    logger.info("   POST   /api/auth/login               - Login")
    logger.info("   GET    /api/auth/verify          🔒  - Verify Token")
    logger.info("   POST   /api/auth/logout              - Logout")
    logger.info("   POST   /api/auth/forgot-password     - Forgot Password")
    logger.info("   POST   /api/auth/reset-password      - Reset Password")
    logger.info("   POST   /api/auth/verify-email        - Verify Email")
    logger.info("   GET    /api/auth/profile         🔒  - Get Profile")
    logger.info("   POST   /api/auth/refresh         🔒  - Refresh Token")
    logger.info("   POST   /api/auth/change-password 🔒  - Change Password")
    logger.info("   DELETE /api/auth/delete-account  🔒  - Delete Account")
    logger.info("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")