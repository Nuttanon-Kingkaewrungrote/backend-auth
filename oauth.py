from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import httpx
import jwt
import json
import urllib.parse
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
WP_SITE_URL = os.getenv('WP_SITE_URL', 'http://localhost')

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
    """รับ code จาก Google แล้ว redirect กลับไป WordPress พร้อม JWT token"""
    login_page = f"{WP_SITE_URL}/%E0%B9%80%E0%B8%82%E0%B9%89%E0%B8%B2%E0%B8%AA%E0%B8%B9%E0%B9%88%E0%B8%A3%E0%B8%B0%E0%B8%9A%E0%B8%9A/"
    
    try:
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
                logger.error(f"Google token exchange failed: {token_response.text}")
                return RedirectResponse(url=f"{login_page}?error=google_failed")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_response.status_code != 200:
                return RedirectResponse(url=f"{login_page}?error=google_user_failed")
            
            google_user = user_response.json()
            google_id = google_user['id']
            google_email = google_user['email']
            
            logger.info(f"Google OAuth: {google_email} (ID: {google_id})")
            conn = get_db()
            
            # ตรวจสอบ OAuth account
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT oa.*, u.* FROM oauth_accounts oa
                    JOIN users u ON oa.user_id = u.id
                    WHERE oa.provider = 'google' AND oa.provider_user_id = %s
                """, (google_id,))
                oauth_account = cur.fetchone()
            
            if oauth_account:
                # มีอยู่แล้ว → Login
                user_id = oauth_account['user_id']
                token_exp = datetime.now() + timedelta(seconds=expires_in)
                with conn.cursor() as cur:
                    cur.execute("UPDATE oauth_accounts SET access_token=%s, refresh_token=%s, token_expires_at=%s, updated_at=NOW() WHERE provider='google' AND provider_user_id=%s",
                        (access_token, refresh_token, token_exp, google_id))
                    cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user_id,))
                conn.commit()
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                    user = cur.fetchone()
                conn.close()
            else:
                # เช็ค email ซ้ำ
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE email=%s", (google_email,))
                    existing_user = cur.fetchone()
                
                if existing_user:
                    user_id = existing_user['id']
                    token_exp = datetime.now() + timedelta(seconds=expires_in)
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO oauth_accounts (user_id,provider,provider_user_id,provider_email,access_token,refresh_token,token_expires_at) VALUES(%s,'google',%s,%s,%s,%s,%s)",
                            (user_id, google_id, google_email, access_token, refresh_token, token_exp))
                        cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user_id,))
                    conn.commit()
                    user = existing_user
                else:
                    username = google_email.split('@')[0] + '_google'
                    with conn.cursor() as cur:
                        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
                        if cur.fetchone():
                            username = f"{username}_{int(datetime.now().timestamp())}"
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO users (username,email,email_verified,role,has_password,oauth_only) VALUES(%s,%s,TRUE,'user',FALSE,TRUE)", (username, google_email))
                        user_id = cur.lastrowid
                        token_exp = datetime.now() + timedelta(seconds=expires_in)
                        cur.execute("INSERT INTO oauth_accounts (user_id,provider,provider_user_id,provider_email,access_token,refresh_token,token_expires_at) VALUES(%s,'google',%s,%s,%s,%s,%s)",
                            (user_id, google_id, google_email, access_token, refresh_token, token_exp))
                    conn.commit()
                    with conn.cursor() as cur:
                        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                        user = cur.fetchone()
                conn.close()
            
            # สร้าง JWT + redirect ไป WordPress
            jwt_token = jwt.encode({
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'exp': datetime.utcnow() + timedelta(days=30)
            }, SECRET_KEY, algorithm=ALGORITHM)
            
            user_json = urllib.parse.quote(json.dumps({
                "id": user['id'],
                "username": user['username'],
                "email": user['email'] or google_email,
                "role": user['role']
            }))
            
            redirect_url = f"{login_page}?google_token={jwt_token}&google_user={user_json}"
            logger.info(f"Google OAuth: Redirecting for user {user['username']}")
            return RedirectResponse(url=redirect_url)
            
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        return RedirectResponse(url=f"{login_page}?error=server_error")


@router.get("/linked-accounts")

# === Google ID Token Verify (Popup Flow) ===
class GoogleTokenRequest(BaseModel):
    credential: str  # ID token จาก Google popup

@router.post("/google/verify")
async def google_verify_token(body: GoogleTokenRequest):
    """Verify Google ID token จาก popup flow แล้ว return JWT"""
    try:
        # Decode Google ID token
        # Google ID token เป็น JWT ที่ sign ด้วย Google's keys
        # เราต้อง verify กับ Google
        async with httpx.AsyncClient() as client:
            # ใช้ Google tokeninfo endpoint
            r = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={body.credential}"
            )
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google token")
            
            google_user = r.json()
            
            # ตรวจสอบ client_id
            if google_user.get('aud') != GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Token not for this app")
            
            google_id = google_user['sub']  # Google user ID
            google_email = google_user['email']
            google_name = google_user.get('name', '')
            google_picture = google_user.get('picture', '')
        
        logger.info(f"Google Popup: {google_email} (ID: {google_id})")
        conn = get_db()
        
        # ตรวจสอบ OAuth account
        with conn.cursor() as cur:
            cur.execute("""
                SELECT oa.*, u.* FROM oauth_accounts oa
                JOIN users u ON oa.user_id = u.id
                WHERE oa.provider = 'google' AND oa.provider_user_id = %s
            """, (google_id,))
            oauth_account = cur.fetchone()
        
        if oauth_account:
            user_id = oauth_account['user_id']
            with conn.cursor() as cur:
                # อัพเดท avatar จาก Google ถ้า user ยังไม่ได้ upload เอง (avatar_url เป็น URL ภายนอก หรือ NULL)
                if google_picture:
                    cur.execute("UPDATE users SET last_login=NOW(), avatar_url=CASE WHEN avatar_url IS NULL OR avatar_url LIKE 'http%%' THEN %s ELSE avatar_url END WHERE id=%s",
                        (google_picture, user_id))
                else:
                    cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user_id,))
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                user = cur.fetchone()
            conn.close()
        else:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email=%s", (google_email,))
                existing_user = cur.fetchone()
            
            if existing_user:
                user_id = existing_user['id']
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO oauth_accounts (user_id,provider,provider_user_id,provider_email) VALUES(%s,'google',%s,%s)",
                        (user_id, google_id, google_email))
                    # อัพเดท avatar + display_name ถ้ายังไม่มี
                    cur.execute("UPDATE users SET last_login=NOW(), avatar_url=COALESCE(avatar_url,%s), display_name=COALESCE(display_name,%s) WHERE id=%s",
                        (google_picture or None, google_name or None, user_id))
                conn.commit()
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                    user = cur.fetchone()
            else:
                username = google_email.split('@')[0]
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
                    if cur.fetchone():
                        username = f"{username}_g{int(datetime.now().timestamp()) % 10000}"
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO users (username,display_name,avatar_url,email,email_verified,role,has_password,oauth_only) VALUES(%s,%s,%s,%s,TRUE,'user',FALSE,TRUE)",
                        (username, google_name or username, google_picture or None, google_email))
                    user_id = cur.lastrowid
                    cur.execute("INSERT INTO oauth_accounts (user_id,provider,provider_user_id,provider_email) VALUES(%s,'google',%s,%s)",
                        (user_id, google_id, google_email))
                conn.commit()
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                    user = cur.fetchone()
            conn.close()
        
        # สร้าง JWT
        jwt_token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(days=30)
        }, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "token": jwt_token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "display_name": user.get('display_name') or user['username'],
                "avatar_url": user.get('avatar_url'),
                "email": user['email'] or google_email,
                "role": user['role']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google verify error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/linked-accounts")
def get_linked_accounts(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """ดูรายการ OAuth providers ที่เชื่อมอยู่"""
    user = _verify_token(credentials)
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT provider, provider_email, created_at FROM oauth_accounts WHERE user_id = %s", (user['user_id'],))
            accounts = cur.fetchall()
        conn.close()
        return {
            "linked_accounts": [
                {"provider": acc['provider'], "email": acc['provider_email'], "linked_at": str(acc['created_at'])}
                for acc in accounts
            ]
        }
    except Exception as e:
        logger.error(f"Get linked accounts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link-google")
async def link_google_account(body: GoogleTokenRequest, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """เชื่อม Google เข้ากับ account ที่ login อยู่"""
    user = _verify_token(credentials)
    
    try:
        # Verify Google token
        async with httpx.AsyncClient() as client:
            r = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={body.credential}")
            if r.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google token")
            google_user = r.json()
            if google_user.get('aud') != GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Token not for this app")
            google_id = google_user['sub']
            google_email = google_user['email']
            google_picture = google_user.get('picture', '')
        
        conn = get_db()
        
        # เช็คว่า Google นี้เชื่อมกับคนอื่นหรือยัง
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM oauth_accounts WHERE provider='google' AND provider_user_id=%s", (google_id,))
            existing = cur.fetchone()
        
        if existing:
            conn.close()
            if existing['user_id'] == user['user_id']:
                raise HTTPException(status_code=400, detail="Google account นี้เชื่อมกับบัญชีของคุณอยู่แล้ว")
            else:
                raise HTTPException(status_code=400, detail="Google account นี้เชื่อมกับบัญชีอื่นแล้ว")
        
        # เชื่อม + อัพเดท avatar ถ้ายังไม่มี
        with conn.cursor() as cur:
            cur.execute("INSERT INTO oauth_accounts (user_id,provider,provider_user_id,provider_email) VALUES(%s,'google',%s,%s)",
                (user['user_id'], google_id, google_email))
            if google_picture:
                cur.execute("UPDATE users SET avatar_url=COALESCE(avatar_url,%s), display_name=COALESCE(display_name,%s) WHERE id=%s",
                    (google_picture, google_user.get('name'), user['user_id']))
        conn.commit()
        conn.close()
        
        logger.info(f"User {user['user_id']} linked Google: {google_email}")
        return {"message": "เชื่อม Google สำเร็จ", "google_email": google_email}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Link Google error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unlink/{provider}")
def unlink_oauth_account(provider: str, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """ยกเลิกการเชื่อม OAuth provider"""
    user = _verify_token(credentials)
    
    if provider not in ['google', 'facebook']:
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    try:
        conn = get_db()
        
        with conn.cursor() as cur:
            cur.execute("SELECT has_password, oauth_only FROM users WHERE id = %s", (user['user_id'],))
            user_data = cur.fetchone()
        
        if user_data['oauth_only'] and not user_data['has_password']:
            conn.close()
            raise HTTPException(status_code=400, detail="ต้องตั้งรหัสผ่านก่อนถึงจะยกเลิกเชื่อม Google ได้")
        
        with conn.cursor() as cur:
            cur.execute("DELETE FROM oauth_accounts WHERE user_id = %s AND provider = %s", (user['user_id'], provider))
            deleted = cur.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted == 0:
            raise HTTPException(status_code=404, detail=f"ไม่ได้เชื่อม {provider} อยู่")
        
        logger.info(f"User {user['user_id']} unlinked {provider}")
        return {"message": f"ยกเลิกเชื่อม {provider} สำเร็จ"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unlink account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _verify_token(credentials):
    """Helper: verify JWT token"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")