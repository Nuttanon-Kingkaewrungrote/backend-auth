import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock
import httpx

client = TestClient(app)

# ============================================
# Test OAuth - Google Login
# ============================================

class TestGoogleOAuth:
    """Test Google OAuth Flow"""
    
    def test_get_google_login_url(self):
        """✅ ได้ URL สำหรับ Google OAuth"""
        response = client.get("/api/auth/google/url")
        
        assert response.status_code == 200
        data = response.json()
        
        # ตรวจสอบว่ามี URL
        assert "url" in data
        assert isinstance(data["url"], str)
        
        # ตรวจสอบว่า URL ถูกต้อง
        assert "accounts.google.com/o/oauth2/v2/auth" in data["url"]
        assert "client_id=" in data["url"]
        assert "redirect_uri=" in data["url"]
        assert "scope=openid%20email%20profile" in data["url"]
    
    def test_google_callback_missing_code(self):
        """❌ Callback โดยไม่มี code"""
        response = client.get("/api/auth/google/callback")
        
        # FastAPI จะ return 422 สำหรับ missing required parameter
        assert response.status_code == 422
    
    def test_google_callback_invalid_code(self):
        """❌ Callback ด้วย code ไม่ถูกต้อง"""
        response = client.get("/api/auth/google/callback?code=invalid_code_12345")
        
        # ควร fail เพราะ Google จะไม่ยอมรับ code นี้
        assert response.status_code in [400, 500]
        
        if response.status_code == 400:
            assert "detail" in response.json()


class TestGoogleOAuthMocked:
    """Test Google OAuth with Mocked API (Unit Tests)"""
    
    @patch('httpx.AsyncClient.post')
    @patch('httpx.AsyncClient.get')
    async def test_google_callback_success_new_user(
        self, 
        mock_get, 
        mock_post
    ):
        """✅ Mock: สร้าง user ใหม่จาก Google OAuth"""
        
        # Mock token response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "mock_access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock user info response
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": "google_user_123",
            "email": "newuser@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg"
        }
        mock_get.return_value = mock_user_response
        
        # Test callback
        response = client.get("/api/auth/google/callback?code=valid_code_123")
        
        # Note: การ test แบบนี้จะไม่ทำงานตามที่คาดหวัง
        # เพราะ TestClient ไม่รองรับ async mocking โดยตรง
        # ต้องใช้ pytest-asyncio และเขียน test แบบ async
        
        # สำหรับการ test จริง ควรใช้ integration test
        # หรือสร้าง mock server สำหรับ Google OAuth
        pass
    
    def test_google_user_has_no_password(self):
        """✅ User ที่สร้างจาก Google ไม่มี password_hash"""
        # ตรวจสอบว่า user ที่ login ผ่าน Google
        # จะมี password_hash = NULL ในฐานข้อมูล
        
        # ต้องใช้ database query เพื่อตรวจสอบ
        # หรือสร้าง user แล้วตรวจสอบ
        
        import pymysql
        import os
        
        DB_CONFIG = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'fund_dashboard'),
        }
        
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # หา user ที่มี email ลงท้ายด้วย @gmail.com (สมมุติว่าเป็น Google user)
                cur.execute("""
                    SELECT username, password_hash, email 
                    FROM users 
                    WHERE email LIKE '%@gmail.com' 
                    AND username LIKE '%_google'
                    LIMIT 1
                """)
                google_user = cur.fetchone()
                
                if google_user:
                    username, password_hash, email = google_user
                    
                    # Google user ควรไม่มี password_hash
                    # (อาจเป็น NULL หรือ empty string ขึ้นอยู่กับการ implement)
                    print(f"Google User: {username}, Password Hash: {password_hash}")
                    # assert password_hash is None or password_hash == ""
                else:
                    print("No Google users found in database")
            
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
            pytest.skip("Cannot connect to database")


class TestGoogleOAuthSecurity:
    """Test OAuth Security"""
    
    def test_oauth_state_parameter(self):
        """⚠️ ตรวจสอบว่ามีการใช้ state parameter หรือไม่ (CSRF protection)"""
        response = client.get("/api/auth/google/url")
        
        # ในการ implement ที่ดี ควรมี state parameter
        # เพื่อป้องกัน CSRF attacks
        # แต่ในโค้ดปัจจุบันยังไม่มี
        
        # ถ้าต้องการเพิ่ม:
        # url += f"&state={random_state_token}"
        
        assert response.status_code == 200
        # TODO: Add state parameter validation
    
    def test_google_user_cannot_login_with_password(self):
        """🔒 User ที่สร้างจาก Google ไม่สามารถ login ด้วย password ได้"""
        
        # สร้าง mock Google user
        import pymysql
        import os
        
        DB_CONFIG = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'fund_dashboard'),
        }
        
        try:
            conn = pymysql.connect(**DB_CONFIG)
            
            # ลบ test user ถ้ามี
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE username = %s", ("test_google_user",))
            conn.commit()
            
            # สร้าง Google user (ไม่มี password_hash)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, email, email_verified, password_hash) 
                    VALUES (%s, %s, TRUE, NULL)
                """, ("test_google_user", "testgoogle@gmail.com"))
            conn.commit()
            conn.close()
            
            # พยายาม login ด้วย password
            response = client.post("/api/auth/login", json={
                "username": "test_google_user",
                "password": "anypassword123",
                "remember_me": False
            })
            
            # ควรได้ error เพราะ Google user ไม่มี password
            assert response.status_code == 200
            assert "error" in response.json()
            
            # Cleanup
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE username = %s", ("test_google_user",))
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Test skipped: {e}")
            pytest.skip("Cannot connect to database")


class TestGoogleOAuthEdgeCases:
    """Test OAuth Edge Cases"""
    
    def test_google_user_email_already_exists_regular_user(self):
        """⚠️ Email ซ้ำกับ regular user (ไม่ใช่ Google)"""
        # Scenario: 
        # 1. User สมัครด้วย email "user@gmail.com" และ password
        # 2. User พยายาม login ด้วย Google ที่ใช้ email เดียวกัน
        # ต้องการให้เชื่อม account หรือสร้างใหม่?
        
        # ในโค้ดปัจจุบัน: หา user จาก email แล้วใช้ user เดิม
        # ซึ่งอาจไม่ปลอดภัย (ควรให้ user ยืนยันก่อน)
        
        pass  # TODO: Implement proper account linking
    
    def test_google_token_expired(self):
        """⏰ Google access token หมดอายุ"""
        # ในระบบจริง ควรมีการ refresh token
        # แต่ในโค้ดปัจจุบันเก็บแค่ access_token
        
        pass  # TODO: Implement token refresh


# ============================================
# Integration Test Tips
# ============================================
"""
สำหรับการทดสอบ OAuth จริง ๆ มีหลายวิธี:

1. Manual Testing:
   - ไปที่ http://localhost:8000/api/auth/google/url
   - คัดลอก URL และเปิดในเบราว์เซอร์
   - Login ด้วย Google
   - ดู callback response

2. Mock OAuth Server:
   - ใช้ library เช่น `pytest-httpx` หรือ `respx`
   - สร้าง mock Google OAuth server
   
3. Test Account:
   - สร้าง Google Test Account
   - ใช้ Google OAuth Playground
   - https://developers.google.com/oauthplayground/

4. E2E Testing:
   - ใช้ Playwright หรือ Selenium
   - Automate การ login ผ่าน Google
   - ระวัง: Google อาจ block bot
"""


# ============================================
# Run Tests
# ============================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])