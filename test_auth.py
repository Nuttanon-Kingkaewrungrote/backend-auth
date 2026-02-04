import pytest
from fastapi.testclient import TestClient
from main import app
import pymysql
import os
import time

# ============================================
# Setup Test Client
# ============================================
client = TestClient(app)

# ตัวแปรเก็บ token และข้อมูลสำหรับ test
test_user = {
    "username": "testuser_auto",
    "password": "password123",
    "email": "test_auto@example.com"
}
auth_token = None
reset_token = None
verification_token = None

# ============================================
# Helper Functions
# ============================================
def cleanup_test_user():
    """ลบ test user ก่อนเริ่ม test"""
    try:
        DB_CONFIG = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'fund_dashboard'),
        }
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE username = %s", (test_user['username'],))
        conn.commit()
        conn.close()
    except:
        pass

# ============================================
# Setup & Teardown
# ============================================
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    """ทำงานก่อนและหลัง test ทั้งหมด"""
    cleanup_test_user()  # ล้างข้อมูลก่อน test
    yield
    cleanup_test_user()  # ล้างข้อมูลหลัง test

# ============================================
# Test Cases
# ============================================

class TestHealthCheck:
    """Test API Health Check"""
    
    def test_home_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "OK"

# ============================================
# Test Register
# ============================================
class TestRegister:
    """Test Registration Flow"""
    
    def test_register_success(self):
        """✅ Register สำเร็จ"""
        response = client.post("/api/auth/register", json=test_user)
        assert response.status_code == 200
        assert "message" in response.json()
        assert "successfully" in response.json()["message"].lower()
    
    def test_register_duplicate_username(self):
        """❌ Register ซ้ำ (username มีอยู่แล้ว)"""
        response = client.post("/api/auth/register", json=test_user)
        assert response.status_code == 200
        assert "error" in response.json()
        assert "already exists" in response.json()["error"].lower()
    
    def test_register_missing_username(self):
        """❌ Register โดยไม่ใส่ username"""
        response = client.post("/api/auth/register", json={
            "username": "",
            "password": "password123",
            "email": "test@example.com"
        })
        assert response.status_code == 200
        assert "error" in response.json()
    
    def test_register_missing_password(self):
        """❌ Register โดยไม่ใส่ password"""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "",
            "email": "test@example.com"
        })
        assert response.status_code == 200
        assert "error" in response.json()
    
    def test_register_invalid_email(self):
        """❌ Register ด้วย email ไม่ถูกต้อง"""
        response = client.post("/api/auth/register", json={
            "username": "newuser2",
            "password": "password123",
            "email": "invalid-email"
        })
        assert response.status_code == 422  # Validation error

# ============================================
# Test Login
# ============================================
class TestLogin:
    """Test Login Flow"""
    
    def test_login_success(self):
        """✅ Login สำเร็จ"""
        global auth_token
        response = client.post("/api/auth/login", json={
            "username": test_user["username"],
            "password": test_user["password"],
            "remember_me": False
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["username"] == test_user["username"]
        
        # เก็บ token ไว้ใช้ใน test อื่น
        auth_token = data["token"]
    
    def test_login_wrong_password(self):
        """❌ Login ด้วย password ผิด"""
        response = client.post("/api/auth/login", json={
            "username": test_user["username"],
            "password": "wrongpassword",
            "remember_me": False
        })
        assert response.status_code == 200
        assert "error" in response.json()
        assert "invalid" in response.json()["error"].lower()
    
    def test_login_wrong_username(self):
        """❌ Login ด้วย username ที่ไม่มี"""
        response = client.post("/api/auth/login", json={
            "username": "nonexistentuser",
            "password": "password123",
            "remember_me": False
        })
        assert response.status_code == 200
        assert "error" in response.json()
    
    def test_login_missing_credentials(self):
        """❌ Login โดยไม่ใส่ข้อมูล"""
        response = client.post("/api/auth/login", json={
            "username": "",
            "password": "",
            "remember_me": False
        })
        assert response.status_code == 200
        assert "error" in response.json()
    
    def test_login_rate_limit(self):
        """⚠️ Test rate limiting (5 requests/minute)"""
        # รอ 1 นาที เพื่อให้ rate limit reset
        time.sleep(61)
        
        # ลองยิง 6 ครั้งติดๆ กัน
        for i in range(6):
            response = client.post("/api/auth/login", json={
                "username": test_user["username"],
                "password": test_user["password"]
            })
            if i < 5:
                assert response.status_code in [200, 429]  # อาจโดน rate limit จาก test ก่อนหน้า
            else:
                assert response.status_code == 429  # ครั้งที่ 6 ต้องโดน rate limit

# ============================================
# Test Protected Endpoints (ต้องใช้ Token)
# ============================================
class TestProtectedEndpoints:
    """Test endpoints ที่ต้องใช้ token"""
    
    def test_verify_token_success(self):
        """✅ Verify token ที่ถูกต้อง"""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["valid"] == True
    
    def test_verify_token_missing(self):
        """❌ Verify โดยไม่มี token"""
        response = client.get("/api/auth/verify")
        assert response.status_code == 401  # แก้จาก 403 เป็น 401
    
    def test_verify_token_invalid(self):
        """❌ Verify ด้วย token ไม่ถูกต้อง"""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401  # Unauthorized
    
    def test_get_profile_success(self):
        """✅ Get profile สำเร็จ"""
        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == test_user["username"]
    
    def test_get_profile_without_token(self):
        """❌ Get profile โดยไม่มี token"""
        response = client.get("/api/auth/profile")
        assert response.status_code == 401  # แก้จาก 403 เป็น 401
    
    def test_get_profile_with_invalid_token(self):
        """❌ Get profile ด้วย token ผิด"""
        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": "Bearer wrong_token"}
        )
        assert response.status_code == 401

# ============================================
# Test Change Password
# ============================================
class TestChangePassword:
    """Test Change Password Flow"""
    
    def test_change_password_success(self):
        """✅ เปลี่ยนรหัสผ่านสำเร็จ"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": test_user["password"],
                "new_password": "newpassword456"
            }
        )
        assert response.status_code == 200
        assert "message" in response.json()
        
        # เปลี่ยนกลับเป็นรหัสเดิม
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": "newpassword456",
                "new_password": test_user["password"]
            }
        )
        assert response.status_code == 200
    
    def test_change_password_wrong_current(self):
        """❌ เปลี่ยนรหัสผ่านด้วย current password ผิด"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456"
            }
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_change_password_too_short(self):
        """❌ รหัสผ่านใหม่สั้นเกินไป (น้อยกว่า 6 ตัว)"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": test_user["password"],
                "new_password": "12345"
            }
        )
        assert response.status_code == 400
        assert "at least 6" in response.json()["detail"].lower()
    
    def test_change_password_same_as_current(self):
        """❌ รหัสผ่านใหม่เหมือนรหัสเดิม"""
        response = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": test_user["password"],
                "new_password": test_user["password"]
            }
        )
        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()
    
    def test_change_password_without_token(self):
        """❌ เปลี่ยนรหัสผ่านโดยไม่มี token"""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": test_user["password"],
                "new_password": "newpassword456"
            }
        )
        assert response.status_code == 401  # แก้จาก 403 เป็น 401

# ============================================
# Test Forgot & Reset Password
# ============================================
class TestForgotResetPassword:
    """Test Forgot Password & Reset Password Flow"""
    
    def test_forgot_password_success(self):
        """✅ ขอรีเซ็ตรหัสผ่านสำเร็จ"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": test_user["email"]}
        )
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_forgot_password_nonexistent_email(self):
        """⚠️ ขอรีเซ็ตด้วย email ที่ไม่มี (ควรได้ response เหมือนกัน - security)"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_forgot_password_invalid_email(self):
        """❌ ขอรีเซ็ตด้วย email format ผิด"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "invalid-email"}
        )
        assert response.status_code == 422
    
    def test_reset_password_invalid_token(self):
        """❌ รีเซ็ตด้วย token ไม่ถูกต้อง"""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid_reset_token",
                "new_password": "newpassword789"
            }
        )
        assert response.status_code == 200
        assert "error" in response.json()

# ============================================
# Test Refresh Token
# ============================================
class TestRefreshToken:
    """Test Refresh Token Flow"""
    
    def test_refresh_token_success(self):
        """✅ Refresh token สำเร็จ"""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "expires_in" in data
    
    def test_refresh_token_without_token(self):
        """❌ Refresh โดยไม่มี token"""
        response = client.post("/api/auth/refresh")
        assert response.status_code == 401  # แก้จาก 403 เป็น 401
    
    def test_refresh_token_invalid(self):
        """❌ Refresh ด้วย token ไม่ถูกต้อง"""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 400

# ============================================
# Test Delete Account
# ============================================
class TestDeleteAccount:
    """Test Delete Account Flow"""
    
    def test_delete_account_wrong_password(self):
        """❌ ลบบัญชีด้วย password ผิด"""
        import json
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            content=json.dumps({
                "password": "wrongpassword",
                "confirm_text": "DELETE"
            })
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_delete_account_wrong_confirm_text(self):
        """❌ ลบบัญชีโดยไม่ใส่ 'DELETE'"""
        import json
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            content=json.dumps({
                "password": test_user["password"],
                "confirm_text": "CONFIRM"
            })
        )
        assert response.status_code == 400
    
    def test_delete_account_without_token(self):
        """❌ ลบบัญชีโดยไม่มี token"""
        import json
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={"Content-Type": "application/json"},
            content=json.dumps({
                "password": test_user["password"],
                "confirm_text": "DELETE"
            })
        )
        assert response.status_code == 401  # แก้จาก 403 เป็น 401
    
    def test_delete_account_success(self):
        """✅ ลบบัญชีสำเร็จ (ทำเป็นขั้นตอนสุดท้าย)"""
        import json
        response = client.request(
            method="DELETE",
            url="/api/auth/delete-account",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            content=json.dumps({
                "password": test_user["password"],
                "confirm_text": "DELETE"
            })
        )
        assert response.status_code == 200
        assert "message" in response.json()
        assert "deleted" in response.json()["message"].lower()
        
# ============================================
# Test Logout
# ============================================
class TestLogout:
    """Test Logout"""
    
    def test_logout_success(self):
        """✅ Logout สำเร็จ"""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert "message" in response.json()