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
from email_service import email_service
from oauth import router as oauth_router


# Load environment variables
load_dotenv()

# Setup logging directory
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

# Application configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-123')
ALGORITHM = 'HS256'

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fund_dashboard'),
}

# Initialize FastAPI app
app = FastAPI(
    title="Fund Dashboard Auth API",
    version="1.0.0",
    description="REST API for Authentication with JWT"
)

# Security scheme for JWT Bearer token
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to verify JWT token and extract user info"""
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ideatradefund.com",
        "https://www.ideatradefund.com",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter setup
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

# Include OAuth router
app.include_router(oauth_router)

def get_db():
    """Create database connection"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

# Pydantic models for request validation
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None  # ไม่บังคับ, ส่งค่าว่างได้

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

class SetPasswordRequest(BaseModel):
    new_password: str

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
    """Health check endpoint for monitoring"""
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

@app.post("/api/auth/register", tags=["Authentication"])
def register(body: RegisterRequest):
    """Register new user"""
    if not body.username or not body.password:
        logger.warning("Register attempt with missing credentials")
        raise HTTPException(status_code=400, detail="Missing username or password")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Validate email format ถ้ามี
    if body.email and '@' not in body.email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # ถ้า email เป็นค่าว่าง ให้เป็น None
    email = body.email.strip() if body.email else None
    if email == '':
        email = None

    hashed = bcrypt.hashpw(body.password.encode('utf-8'), bcrypt.gensalt())
    verification_token = secrets.token_urlsafe(32)

    try:
        conn = get_db()
        
        # เช็ค email ซ้ำ (ถ้ามี email)
        if email:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    conn.close()
                    logger.warning(f"Register failed: Email '{email}' already exists")
                    raise HTTPException(status_code=409, detail="อีเมลนี้ถูกใช้แล้ว กรุณาเข้าสู่ระบบหรือกดลืมรหัสผ่าน")
        
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, email, verification_token) VALUES (%s, %s, %s, %s)",
                (body.username, hashed.decode('utf-8'), email, verification_token)
            )
        conn.commit()
        conn.close()

        logger.info(f"New user registered: {body.username}")
        
        # Send verification email if email is provided
        if email:
            email_service.send_verification_email(email, body.username, verification_token)
            logger.info(f"Verification email sent to: {email}")
        
        return {"message": "สมัครสมาชิกสำเร็จ!" + (" กรุณาตรวจสอบอีเมลเพื่อยืนยันบัญชี" if email else "")}

    except HTTPException:
        raise
    except pymysql.IntegrityError:
        logger.warning(f"Register failed: Username '{body.username}' already exists")
        raise HTTPException(status_code=409, detail="Username นี้ถูกใช้แล้ว กรุณาเลือกชื่ออื่น")
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login", tags=["Authentication"])
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    """
    User login with username/email and password
    
    รับได้ทั้ง:
    - username: "john_doe"
    - email: "john@gmail.com"
    """
    logger.info(f"Login attempt for: {body.username} from IP: {request.client.host}")
    
    if not body.username or not body.password:
        return {"error": "Missing credentials"}

    try:
        conn = get_db()
        
        # ตรวจสอบว่าเป็น email หรือ username
        if '@' in body.username:
            # Login ด้วย email
            logger.info(f"Login with email: {body.username}")
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (body.username,))
                user = cur.fetchone()
        else:
            # Login ด้วย username
            logger.info(f"Login with username: {body.username}")
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (body.username,))
                user = cur.fetchone()

        # Check if user exists and has password (not OAuth-only user)
        if user and user['password_hash'] and bcrypt.checkpw(body.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Update last login timestamp
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()

            # Generate JWT token
            token_expires = timedelta(days=30) if body.remember_me else timedelta(hours=24)
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + token_expires
            }, SECRET_KEY, algorithm=ALGORITHM)

            conn.close()
            
            logger.info(f"Login successful for user: {user['username']}")
            
            return {
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "display_name": user.get('display_name') or user['username'],
                    "avatar_url": user.get('avatar_url'),
                    "email": user['email'],
                    "role": user['role']
                },
                "expires_in": 30 * 24 * 3600 if body.remember_me else 24 * 3600
            }

        conn.close()
        logger.warning(f"Login failed for: {body.username} - Invalid credentials")
        return {"error": "Invalid username/email or password"}

    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"error": str(e)}
    

@app.get("/api/auth/verify", tags=["Authentication"])
def verify(user: dict = Depends(get_current_user)):
    """Verify JWT token validity"""
    return {"valid": True, "user": user}

@app.post("/api/auth/logout", tags=["Authentication"])
def logout():
    """User logout"""
    return {"message": "Logged out successfully"}

@app.post("/api/auth/forgot-password", tags=["Authentication"])
def forgot_password(body: ForgotPasswordRequest):
    """Request password reset link"""
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
            
            # Send password reset email
            email_service.send_password_reset_email(body.email, reset_token)
            logger.info(f"Password reset email sent to: {body.email}")

        conn.close()
        # Don't reveal if email exists (security best practice)
        return {"message": "If the email exists, a password reset link has been sent"}

    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return {"error": str(e)}

@app.post("/api/auth/reset-password", tags=["Authentication"])
def reset_password(body: ResetPasswordRequest):
    """Reset password using token"""
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
    """Verify email using token"""
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
    

@app.get("/api/auth/profile", tags=["User Management"])
def get_profile(user: dict = Depends(get_current_user)):
    """Get user profile information"""
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
    """Refresh access token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    try:
        # Decode token without expiration check
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})

        # Generate new token
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
    """Change user password"""
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
        
        # Send email notification
        if user_data['email']:
            email_service.send_password_changed_email(user_data['email'], user['username'])
            logger.info(f"Password change notification sent to: {user_data['email']}")
        
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/auth/delete-account", tags=["User Management"])
def delete_account(body: DeleteAccountRequest, user: dict = Depends(get_current_user)):
    """Delete user account"""
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

        # Delete user (cascade will delete oauth_accounts)
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
    
@app.post("/api/auth/set-password", tags=["User Management"])
def set_password(body: SetPasswordRequest, user: dict = Depends(get_current_user)):
    """
    ตั้งรหัสผ่านสำหรับ user ที่สมัครผ่าน OAuth
    (ใช้เมื่อต้องการ unlink OAuth account)
    """
    if not body.new_password or len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT has_password FROM users WHERE id = %s", (user['user_id'],))
            user_data = cur.fetchone()
        
        if not user_data:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_data['has_password']:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="You already have a password. Use change-password instead."
            )
        
        # Hash password
        hashed = bcrypt.hashpw(body.new_password.encode('utf-8'), bcrypt.gensalt())
        
        # อัปเดท password
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET password_hash = %s, has_password = TRUE, oauth_only = FALSE
                WHERE id = %s
            """, (hashed.decode('utf-8'), user['user_id']))
        conn.commit()
        conn.close()
        
        logger.info(f"User {user['user_id']} set password (was OAuth-only)")
        
        return {"message": "Password set successfully. You can now login with username/password."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Set password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/account-info", tags=["User Management"])
def get_account_info(user: dict = Depends(get_current_user)):
    """
    ดูข้อมูล account รวมถึง OAuth providers ที่เชื่อมอยู่
    """
    try:
        conn = get_db()
        
        # ดึงข้อมูล user
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, display_name, avatar_url, email, role, has_password, oauth_only, created_at, last_login
                FROM users 
                WHERE id = %s
            """, (user['user_id'],))
            user_data = cur.fetchone()
        
        # ดึง OAuth accounts
        with conn.cursor() as cur:
            cur.execute("""
                SELECT provider, provider_email, created_at
                FROM oauth_accounts
                WHERE user_id = %s
            """, (user['user_id'],))
            oauth_accounts = cur.fetchall()
        
        conn.close()
        
        return {
            "user": {
                "id": user_data['id'],
                "username": user_data['username'],
                "display_name": user_data.get('display_name') or user_data['username'],
                "avatar_url": user_data.get('avatar_url'),
                "email": user_data['email'],
                "role": user_data['role'],
                "has_password": user_data['has_password'],
                "oauth_only": user_data['oauth_only'],
                "created_at": str(user_data['created_at']),
                "last_login": str(user_data['last_login']) if user_data['last_login'] else None
            },
            "linked_accounts": [
                {
                    "provider": acc['provider'],
                    "email": acc['provider_email'],
                    "linked_at": str(acc['created_at'])
                }
                for acc in oauth_accounts
            ]
        }
        
    except Exception as e:
        logger.error(f"Get account info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None

@app.post("/api/auth/update-profile", tags=["User Management"])
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """อัพเดทชื่อแสดง"""
    try:
        if body.display_name is not None:
            name = body.display_name.strip()
            if len(name) < 1 or len(name) > 100:
                raise HTTPException(status_code=400, detail="ชื่อต้องมี 1-100 ตัวอักษร")
        
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET display_name = %s WHERE id = %s", (body.display_name, user['user_id']))
        conn.commit()
        conn.close()
        
        logger.info(f"User {user['user_id']} updated display_name to: {body.display_name}")
        return {"message": "อัพเดทโปรไฟล์สำเร็จ"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import File, UploadFile
import uuid

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/auth/upload-avatar", tags=["User Management"])
async def upload_avatar(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """อัพโหลดรูปโปรไฟล์"""
    try:
        # เช็คประเภทไฟล์
        allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if file.content_type not in allowed:
            raise HTTPException(status_code=400, detail="รองรับเฉพาะ JPG, PNG, GIF, WEBP")
        
        # เช็คขนาด (max 2MB)
        contents = await file.read()
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="ไฟล์ต้องไม่เกิน 2MB")
        
        # สร้างชื่อไฟล์
        ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'jpg'
        filename = f"{user['user_id']}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # ลบรูปเก่า
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT avatar_url FROM users WHERE id = %s", (user['user_id'],))
            old = cur.fetchone()
            if old and old.get('avatar_url'):
                old_file = os.path.join(UPLOAD_DIR, os.path.basename(old['avatar_url']))
                if os.path.exists(old_file):
                    os.remove(old_file)
        
        # บันทึกไฟล์
        with open(filepath, 'wb') as f:
            f.write(contents)
        
        # อัพเดท DB
        avatar_url = f"/uploads/avatars/{filename}"
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET avatar_url = %s WHERE id = %s", (avatar_url, user['user_id']))
        conn.commit()
        conn.close()
        
        logger.info(f"User {user['user_id']} uploaded avatar: {filename}")
        return {"message": "อัพโหลดรูปสำเร็จ", "avatar_url": avatar_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload avatar error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve uploaded files
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")), name="uploads")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info(" FastAPI Server Starting...")
    logger.info(" URL:  http://localhost:8000")
    logger.info(" Docs: http://localhost:8000/docs")
    logger.info("=" * 50)
    logger.info("\n Available Endpoints:")
    logger.info("   GET    /                             - API Info")
    logger.info("   GET    /health                       - Health Check")
    logger.info("   POST   /api/auth/register            - Register")
    logger.info("   POST   /api/auth/login               - Login")
    logger.info("   GET    /api/auth/verify          (token)  - Verify Token")
    logger.info("   POST   /api/auth/logout              - Logout")
    logger.info("   POST   /api/auth/forgot-password     - Forgot Password")
    logger.info("   POST   /api/auth/reset-password      - Reset Password")
    logger.info("   POST   /api/auth/verify-email        - Verify Email")
    logger.info("   GET    /api/auth/profile         (token)  - Get Profile")
    logger.info("   POST   /api/auth/refresh         (token)  - Refresh Token")
    logger.info("   POST   /api/auth/change-password (token) - Change Password")
    logger.info("   DELETE /api/auth/delete-account  (token)  - Delete Account")
    logger.info("   GET    /api/auth/google/url          - Google OAuth URL")
    logger.info("   POST   /api/auth/google/callback     - Google OAuth Callback")
    logger.info("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")