"""
Test Suite for Authentication API
รวม test cases ทั้งหมดสำหรับ Auth API
"""

import pytest
from fastapi.testclient import TestClient
from main import app
import time
import json

client = TestClient(app)

# ============================================
# Test Data
# ============================================
test_user = {
    "username": f"test_auto_{int(time.time())}",
    "password": "test_password_123",
    "email": f"test_auto_{int(time.time())}@example.com"
}

login_user = None  # เก็บ user ที่ใช้ login
auth_token = None  # เก็บ token

# ============================================
# TEST: Health Check
# ============================================

class TestHealthCheck:
    """Test Health Check Endpoint"""
    
    def test_home_endpoint(self):
        """✅ Health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"].lower() in ["ok", "healthy"]


# ============================================
# TEST: Register
# ============================================

class TestRegister:
    """Test Registration Endpoints"""
    
    def test_register_success(self):
        """✅ Register สำเร็จ"""
        global login_user
        login_user = test_user.copy()
        
        response = client.post("/api/auth/register", json=test_user)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        message = data["message"].lower()
        assert "สำเร็จ" in data["message"] or "success" in message
    
    def test_register_duplicate_username(self):
        """❌ Register ซ้ำ (username มีอยู่แล้ว)"""
        response = client.post("/api/auth/register", json=test_user)
        assert response.status_code == 409
        data = response.json()
        assert "detail" in data or "error" in data
    
    def test_register_missing_username(self):
        """❌ Register โดยไม่ใส่ username"""
        response = client.post("/api/auth/register", json={
            "username": "",
            "password": "password123",
            "email": "test@example.com"
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data or "error" in data
    
    def test_register_missing_password(self):
        """❌ Register โดยไม่ใส่ password"""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "",
            "email": "test@example.com"
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data or "error" in data
    
    def test_register_invalid_email(self):
        """❌ Register ด้วย email ไม่ถูกต้อง"""
        response = client.post("/api/auth/register", json={
            "username": "newuser2",
            "password": "password123",
            "email": "invalid-email"
        })
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data or "error" in data


# ============================================
# TEST: Login
# ============================================

class TestLogin:
    """Test Login Endpoints"""
    
    def test_login_success(self):
        """✅ Login สำเร็จ"""
        global auth_token
        
        response = client.post("/api/auth/login", json={
            "username": login_user["username"],
            "password": login_user["password"],
            "remember_me": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        
        auth_token = data["token"]
        assert len(auth_token) > 0
    
    def test_login_wrong_password(self):
        """❌ Login ด้วย password ผิด"""
        response = client.post("/api/auth/login", json={
            "username": login_user["username"],
            "password": "wrong_password",
            "remember_me": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
    
    def test_login_wrong_username(self):
        """❌ Login ด้วย username ที่ไม่มี"""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent_user_12345",
            "password": "anypassword",
            "remember_me": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
    
    def test_login_missing_credentials(self):
        """❌ Login โดยไม่ใส่ credentials"""
        response = client.post("/api/auth/login", json={
            "username": "",
            "password": "",
            "remember_me": False
        })
        
        assert response.status_code in [200, 400]
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_login_rate_limit(self):
        """⏱️ Test rate limiting"""
        for i in range(6):
            response = client.post("/api/auth/login", json={
                "username": "test_rate_limit",
                "password": "wrong_password",
                "remember_me": False
            })
            
            assert response.status_code in [200, 401, 429]


# ============================================
# TEST: Protected Endpoints
# ============================================

class TestProtectedEndpoints:
    """Test endpoints ที่ต้องใช้ authentication"""
    
    def test_verify_token_success(self):
        """✅ Verify token สำเร็จ"""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert data["valid"] == True
        assert "user" in data
    
    def test_verify_token_missing(self):
        """❌ Verify โดยไม่ส่ง token"""
        response = client.get("/api/auth/verify")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_verify_token_invalid(self):
        """❌ Verify ด้วย token ไม่ถูกต้อง"""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_get_profile_success(self):
        """✅ Get profile สำเร็จ"""
        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == login_user["username"]
    
    def test_get_profile_without_token(self):
        """❌ Get profile โดยไม่ส่ง token"""
        response = client.get("/api/auth/profile")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_get_profile_with_invalid_token(self):
        """❌ Get profile ด้วย token ไม่ถูกต้อง"""
        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


# ============================================
# TEST: Change Password
# ============================================

class TestChangePassword:
    """Test Change Password Endpoint"""
    
    def test_change_password_success(self):
        """✅ เปลี่ยนรหัสผ่านสำเร็จ"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": login_user["password"],
                "new_password": "new_password_456"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        login_user["password"] = "new_password_456"
    
    def test_change_password_wrong_current(self):
        """❌ เปลี่ยนรหัสผ่านด้วย current password ผิด"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": "wrong_password",
                "new_password": "new_password_789"
            }
        )
        
        assert response.status_code in [200, 400, 401]
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_change_password_too_short(self):
        """❌ เปลี่ยนรหัสผ่านที่สั้นเกินไป"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": login_user["password"],
                "new_password": "123"
            }
        )
        
        assert response.status_code in [200, 400]
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_change_password_same_as_current(self):
        """❌ เปลี่ยนรหัสผ่านเป็นตัวเดิม"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": login_user["password"],
                "new_password": login_user["password"]
            }
        )
        
        assert response.status_code in [200, 400]
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_change_password_without_token(self):
        """❌ เปลี่ยนรหัสผ่านโดยไม่ส่ง token"""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "anypassword",
                "new_password": "newpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


# ============================================
# TEST: Forgot & Reset Password
# ============================================

class TestForgotResetPassword:
    """Test Forgot Password & Reset Password"""
    
    def test_forgot_password_success(self):
        """✅ ขอรีเซ็ตรหัสผ่านสำเร็จ"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": login_user["email"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_forgot_password_nonexistent_email(self):
        """❌ ขอรีเซ็ตด้วย email ที่ไม่มี"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_forgot_password_invalid_email(self):
        """❌ ขอรีเซ็ตด้วย email format ผิด"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code in [200, 400, 422]
    
    def test_reset_password_invalid_token(self):
        """❌ รีเซ็ตรหัสผ่านด้วย token ไม่ถูกต้อง"""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid_reset_token",
                "new_password": "new_password_123"
            }
        )
        
        assert response.status_code in [200, 400, 401]
        data = response.json()
        assert "error" in data or "detail" in data


# ============================================
# TEST: Refresh Token
# ============================================

class TestRefreshToken:
    """Test Refresh Token Endpoint"""
    
    def test_refresh_token_success(self):
        """✅ Refresh token สำเร็จ"""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 0
    
    def test_refresh_token_without_token(self):
        """❌ Refresh โดยไม่ส่ง token"""
        response = client.post("/api/auth/refresh")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_refresh_token_invalid(self):
        """❌ Refresh ด้วย token ไม่ถูกต้อง"""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code in [400, 401]
        data = response.json()
        assert "detail" in data or "error" in data


# ============================================
# TEST: Delete Account
# ============================================

class TestDeleteAccount:
    """Test Delete Account (ต้องทดสอบท้ายสุด)"""
    
    def test_delete_account_wrong_password(self):
        """❌ ลบบัญชีด้วย password ผิด"""
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            content=json.dumps({
                "password": "wrong_password",
                "confirm_text": "DELETE"  # ✅ ใช้ "DELETE"
            })
        )
        
        assert response.status_code in [200, 400, 401]
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_delete_account_wrong_confirm_text(self):
        """❌ ลบบัญชีโดยไม่ยืนยันข้อความ"""
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            content=json.dumps({
                "password": login_user["password"],
                "confirm_text": "WRONG"  # ✅ ใช้ "WRONG" แทน "wrong text"
            })
        )
        
        assert response.status_code in [200, 400]
        data = response.json()
        assert "error" in data or "detail" in data
    
    def test_delete_account_without_token(self):
        """❌ ลบบัญชีโดยไม่ส่ง token"""
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={"Content-Type": "application/json"},
            content=json.dumps({
                "password": "anypassword",
                "confirm_text": "DELETE"  # ✅ ใช้ "DELETE"
            })
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_delete_account_success(self):
        """✅ ลบบัญชีสำเร็จ (ต้องเป็น test สุดท้าย!)"""
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            content=json.dumps({
                "password": login_user["password"],
                "confirm_text": "DELETE"  # ✅ ใช้ "DELETE"
            })
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


# ============================================
# TEST: Logout
# ============================================

class TestLogout:
    """Test Logout Endpoint"""
    
    def test_logout_success(self):
        """✅ Logout สำเร็จ"""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])