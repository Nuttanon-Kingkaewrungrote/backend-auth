from fastapi import APIRouter, HTTPException, Depends, Query
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
async def google_callback(code: str, link_account: bool = Query(False)):
    """
    รับ code จาก Google และแลกเป็น access token
    
    Parameters:
    - code: Authorization code จาก Google
    - link_account: True = เชื่อม Google กับ account ที่มีอยู่, False = สร้างใหม่หรือ login
    """
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
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            
            # 2. ดึงข้อมูล user จาก Google
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            
            google_user = user_response.json()
            google_id = google_user['id']
            google_email = google_user['email']
            google_name = google_user.get('name', '')
            
            logger.info(f"Google OAuth: {google_email} (ID: {google_id})")
            
            conn = get_db()
            
            # 3. ตรวจสอบว่ามี OAuth account นี้อยู่แล้วหรือไม่
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT oa.*, u.* 
                    FROM oauth_accounts oa
                    JOIN users u ON oa.user_id = u.id
                    WHERE oa.provider = 'google' AND oa.provider_user_id = %s
                """, (google_id,))
                oauth_account = cur.fetchone()
            
            if oauth_account:
                # 3.1 มี OAuth account แล้ว → Login
                user_id = oauth_account['user_id']
                
                # อัปเดท access token
                token_expires = datetime.now() + timedelta(seconds=expires_in)
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE oauth_accounts 
                        SET access_token = %s, 
                            refresh_token = %s,
                            token_expires_at = %s,
                            updated_at = NOW()
                        WHERE provider = 'google' AND provider_user_id = %s
                    """, (access_token, refresh_token, token_expires, google_id))
                    
                    cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
                conn.commit()
                
                # ดึงข้อมูล user
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    user = cur.fetchone()
                
                conn.close()
                
                logger.info(f"Google OAuth: Existing user login - {user['username']}")
                
            else:
                # 3.2 ไม่มี OAuth account → ตรวจสอบว่ามี user ด้วย email เดียวกันหรือไม่
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE email = %s", (google_email,))
                    existing_user = cur.fetchone()
                
                if existing_user:
                    # 3.2.1 มี user ด้วย email เดียวกัน → Account Linking
                    user_id = existing_user['id']
                    
                    logger.info(f"Google OAuth: Linking to existing account - {existing_user['username']}")
                    
                    # สร้าง OAuth account record
                    token_expires = datetime.now() + timedelta(seconds=expires_in)
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO oauth_accounts 
                            (user_id, provider, provider_user_id, provider_email, access_token, refresh_token, token_expires_at)
                            VALUES (%s, 'google', %s, %s, %s, %s, %s)
                        """, (user_id, google_id, google_email, access_token, refresh_token, token_expires))
                        
                        # อัปเดท last_login
                        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
                    conn.commit()
                    
                    user = existing_user
                    
                else:
                    # 3.2.2 ไม่มี user เลย → สร้างใหม่
                    username = google_email.split('@')[0] + '_google'
                    
                    # ตรวจสอบว่า username ซ้ำหรือไม่
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                        if cur.fetchone():
                            # ถ้าซ้ำ เพิ่ม timestamp
                            username = f"{username}_{int(datetime.now().timestamp())}"
                    
                    logger.info(f"Google OAuth: Creating new user - {username}")
                    
                    # สร้าง user ใหม่
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO users 
                            (username, email, email_verified, role, has_password, oauth_only) 
                            VALUES (%s, %s, TRUE, 'user', FALSE, TRUE)
                        """, (username, google_email))
                        user_id = cur.lastrowid
                        
                        # สร้าง OAuth account
                        token_expires = datetime.now() + timedelta(seconds=expires_in)
                        cur.execute("""
                            INSERT INTO oauth_accounts 
                            (user_id, provider, provider_user_id, provider_email, access_token, refresh_token, token_expires_at)
                            VALUES (%s, 'google', %s, %s, %s, %s, %s)
                        """, (user_id, google_id, google_email, access_token, refresh_token, token_expires))
                    conn.commit()
                    
                    # ดึงข้อมูล user ที่สร้างใหม่
                    with conn.cursor() as cur:
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
                    "role": user['role'],
                    "has_password": user.get('has_password', True),
                    "oauth_providers": ["google"]
                },
                "expires_in": 30 * 24 * 3600,
                "linked": oauth_account is None and existing_user is not None  # True ถ้าเพิ่ง link
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/linked-accounts")
def get_linked_accounts(user: dict = Depends(lambda: None)):
    """
    ดูรายการ OAuth providers ที่เชื่อมอยู่
    TODO: เพิ่ม authentication dependency
    """
    # TODO: ใช้ get_current_user dependency
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT provider, provider_email, created_at
                FROM oauth_accounts
                WHERE user_id = %s
            """, (user['user_id'],))
            accounts = cur.fetchall()
        conn.close()
        
        return {
            "linked_accounts": [
                {
                    "provider": acc['provider'],
                    "email": acc['provider_email'],
                    "linked_at": str(acc['created_at'])
                }
                for acc in accounts
            ]
        }
    except Exception as e:
        logger.error(f"Get linked accounts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unlink/{provider}")
def unlink_oauth_account(provider: str, user: dict = Depends(lambda: None)):
    """
    ยกเลิกการเชื่อม OAuth provider
    TODO: เพิ่ม authentication dependency
    """
    # TODO: ใช้ get_current_user dependency
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if provider not in ['google', 'facebook']:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    try:
        conn = get_db()
        
        # ตรวจสอบว่า user มี password หรือไม่
        with conn.cursor() as cur:
            cur.execute("SELECT has_password, oauth_only FROM users WHERE id = %s", (user['user_id'],))
            user_data = cur.fetchone()
        
        if user_data['oauth_only'] and not user_data['has_password']:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Cannot unlink. You must set a password first (this is your only login method)"
            )
        
        # ลบ OAuth account
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM oauth_accounts
                WHERE user_id = %s AND provider = %s
            """, (user['user_id'], provider))
            deleted = cur.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail=f"{provider} account not linked")
        
        logger.info(f"User {user['user_id']} unlinked {provider}")
        
        return {"message": f"{provider.capitalize()} account unlinked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unlink account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))