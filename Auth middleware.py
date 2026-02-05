"""
Auth Middleware สำหรับ Backend Services อื่น
ใช้สำหรับตรวจสอบ JWT Token ในระบบ Fund Dashboard

Created for: Backend Team Integration
Author: Authentication Service
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-123')
ALGORITHM = 'HS256'
security = HTTPBearer(auto_error=False)


# ============================================
# Main Authentication Functions
# ============================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    ตรวจสอบ JWT Token และคืนข้อมูล user (บังคับต้องมี token)
    
    Returns:
        dict: {'user_id': int, 'username': str, 'role': str, 'exp': int}
    
    Example:
        @app.get("/api/funds/my-portfolio")
        def get_my_portfolio(user: dict = Depends(get_current_user)):
            user_id = user['user_id']
            return {"user_id": user_id, "portfolio": [...]}
    """
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


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    ตรวจสอบ JWT Token แต่ไม่บังคับต้องมี (สำหรับ endpoint ที่ login ไม่บังคับ)
    
    Returns:
        dict | None: ข้อมูล user ถ้ามี, None ถ้าไม่มี
    
    Example:
        @app.get("/api/funds/list")
        def list_funds(user: dict = Depends(get_optional_user)):
            if user:
                # แสดงกองทุนที่แนะนำตาม user
                return {"personalized": True, "user_id": user['user_id']}
            else:
                # แสดงกองทุนทั่วไป
                return {"personalized": False}
    """
    if credentials is None:
        return None
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None


def require_role(allowed_roles: list):
    """
    ตรวจสอบว่า user มี role ที่อนุญาตหรือไม่
    
    Example:
        @app.get("/api/admin/users")
        def get_all_users(
            user: dict = Depends(get_current_user),
            _: None = Depends(require_role(['admin']))
        ):
            return {"users": [...]}
    """
    def role_checker(user: dict = Depends(get_current_user)):
        if user['role'] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return None
    return role_checker


# ============================================
# Utility Functions
# ============================================

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    ตรวจสอบ token โดยตรง (สำหรับใช้นอก FastAPI)
    
    Args:
        token: JWT token string
    
    Returns:
        dict | None: ข้อมูล user ถ้า token ถูกต้อง, None ถ้าไม่ถูกต้อง
    
    Example:
        from auth_middleware import verify_token
        
        user = verify_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
        if user:
            print(f"User ID: {user['user_id']}")
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    ดึง user_id จาก token
    
    Args:
        token: JWT token string
    
    Returns:
        int | None: user_id ถ้า token ถูกต้อง
    """
    user = verify_token(token)
    return user['user_id'] if user else None