from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pymysql
import logging

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["OAuth"])

# Google OAuth Config
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-123')
ALGORITHM = 'HS256'

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fund_dashboard'),
}


class GoogleTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

def get_db():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

@router.get("/google/url")
def get_google_login_url():
    """สร้าง URL สำหรับ Google OAuth"""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline"
    )
    return {"url": google_auth_url}

@router.get("/google/callback")
async def google_callback(code: str):
    """รับ code จาก Google และแลกเป็น access token"""
    try:
        # 1. แลก code เป็น access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            # 2. ดึงข้อมูล user จาก Google
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            google_user = user_response.json()
            
            # 3. ตรวจสอบว่ามี user ในระบบหรือไม่
            conn = get_db()
            with conn.cursor() as cur:
                # หา user จาก email
                cur.execute("SELECT * FROM users WHERE email = %s", (google_user['email'],))
                user = cur.fetchone()
                
                if not user:
                    # สร้าง user ใหม่
                    username = google_user['email'].split('@')[0] + '_google'
                    cur.execute(
                        """INSERT INTO users (username, email, email_verified, role) 
                           VALUES (%s, %s, TRUE, 'user')""",
                        (username, google_user['email'])
                    )
                    conn.commit()
                    user_id = cur.lastrowid
                    
                    logger.info(f"New Google user created: {username}")
                else:
                    user_id = user['id']
                    # อัปเดท last_login
                    cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
                    conn.commit()
                    
                    logger.info(f"Google login successful: {user['username']}")
                
                # ดึงข้อมูล user อีกครั้งหลัง insert/update
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
            
            conn.close()
            
            # 4. สร้าง JWT token
            token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + timedelta(days=30)
            }, SECRET_KEY, algorithm=ALGORITHM)
            
            return {
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "role": user['role']
                },
                "expires_in": 30 * 24 * 3600
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))