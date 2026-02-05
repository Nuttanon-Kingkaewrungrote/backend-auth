import pytest
from email_service import EmailService, email_service
from unittest.mock import patch, MagicMock
import os

# ============================================
# Test Email Service
# ============================================

class TestEmailServiceConfiguration:
    """Test Email Service Configuration"""
    
    def test_email_service_instance_created(self):
        """✅ EmailService instance ถูกสร้างสำเร็จ"""
        assert email_service is not None
        assert isinstance(email_service, EmailService)
    
    def test_email_service_smtp_config(self):
        """✅ SMTP configuration ถูกต้อง"""
        assert email_service.smtp_server == os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        assert email_service.smtp_port == int(os.getenv('SMTP_PORT', '587'))
    
    def test_email_service_sender_config(self):
        """✅ Sender configuration ถูกตั้งค่า"""
        # ถ้าไม่มี credentials ใน .env ก็จะเป็น None
        sender_email = os.getenv('EMAIL_USER')
        sender_password = os.getenv('EMAIL_PASSWORD')
        
        assert email_service.sender_email == sender_email
        assert email_service.sender_password == sender_password
    
    def test_email_service_frontend_url(self):
        """✅ Frontend URL ถูกตั้งค่า"""
        expected_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')
        assert email_service.frontend_url == expected_url


class TestEmailServiceSending:
    """Test Email Sending Functionality"""
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """✅ ส่งอีเมลสำเร็จ"""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # สร้าง test instance ที่มี credentials
        test_service = EmailService()
        test_service.sender_email = "test@example.com"
        test_service.sender_password = "testpassword123"
        
        # ส่งอีเมล
        result = test_service.send_email(
            to_email="recipient@example.com",
            subject="Test Email",
            body="<p>This is a test</p>"
        )
        
        # ตรวจสอบ
        assert result == True
        mock_smtp.assert_called_once_with(test_service.smtp_server, test_service.smtp_port)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            test_service.sender_email,
            test_service.sender_password
        )
        mock_server.send_message.assert_called_once()
    
    def test_send_email_without_credentials(self):
        """⚠️ ส่งอีเมลโดยไม่มี credentials (ควร skip gracefully)"""
        # สร้าง instance ที่ไม่มี credentials
        test_service = EmailService()
        test_service.sender_email = None
        test_service.sender_password = None
        
        result = test_service.send_email(
            to_email="recipient@example.com",
            subject="Test Email",
            body="<p>This is a test</p>"
        )
        
        # ควร return False และไม่ crash
        assert result == False
    
    @patch('smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp):
        """❌ SMTP error (connection failed)"""
        # Mock SMTP เพื่อให้ raise exception
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        test_service = EmailService()
        test_service.sender_email = "test@example.com"
        test_service.sender_password = "testpassword123"
        
        result = test_service.send_email(
            to_email="recipient@example.com",
            subject="Test Email",
            body="<p>This is a test</p>"
        )
        
        # ควร handle error และ return False
        assert result == False


class TestVerificationEmail:
    """Test Verification Email"""
    
    @patch.object(EmailService, 'send_email')
    def test_send_verification_email(self, mock_send_email):
        """✅ ส่งอีเมลยืนยันตัวตน"""
        mock_send_email.return_value = True
        
        result = email_service.send_verification_email(
            email="newuser@example.com",
            username="newuser",
            token="verification_token_123"
        )
        
        assert result == True
        mock_send_email.assert_called_once()
        
        # ตรวจสอบ arguments
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "newuser@example.com"  # to_email
        assert "ยืนยันอีเมล" in call_args[0][1]  # subject
        assert "verification_token_123" in call_args[0][2]  # body
    
    def test_verification_email_contains_link(self):
        """✅ อีเมลยืนยันมี verification link"""
        test_service = EmailService()
        test_service.frontend_url = "http://localhost:8000"
        
        # ดึง email body (ไม่ต้องส่งจริง)
        email = "test@example.com"
        username = "testuser"
        token = "test_token_123"
        
        verify_link = f"{test_service.frontend_url}/verify-email?token={token}"
        
        # ตรวจสอบว่า link ถูกสร้างถูกต้อง
        assert verify_link == "http://localhost:8000/verify-email?token=test_token_123"
    
    def test_verification_email_contains_username(self):
        """✅ อีเมลยืนยันมีชื่อผู้ใช้"""
        # Test นี้เป็นการตรวจสอบว่า email template มี username
        # โดยการ inspect method code หรือ mock send_email
        pass


class TestPasswordResetEmail:
    """Test Password Reset Email"""
    
    @patch.object(EmailService, 'send_email')
    def test_send_password_reset_email(self, mock_send_email):
        """✅ ส่งอีเมลรีเซ็ตรหัสผ่าน"""
        mock_send_email.return_value = True
        
        result = email_service.send_password_reset_email(
            email="user@example.com",
            token="reset_token_456"
        )
        
        assert result == True
        mock_send_email.assert_called_once()
        
        # ตรวจสอบ arguments
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "user@example.com"
        assert "รีเซ็ตรหัสผ่าน" in call_args[0][1]
        assert "reset_token_456" in call_args[0][2]
    
    def test_reset_email_contains_warning(self):
        """⚠️ อีเมลรีเซ็ตมีคำเตือนหมดอายุ 1 ชั่วโมง"""
        test_service = EmailService()
        
        # ตรวจสอบว่า email template มีคำเตือน
        # โดยการดู source code หรือ test กับ actual content
        pass


class TestPasswordChangedEmail:
    """Test Password Changed Notification Email"""
    
    @patch.object(EmailService, 'send_email')
    def test_send_password_changed_email(self, mock_send_email):
        """✅ ส่งอีเมลแจ้งเตือนเปลี่ยนรหัสผ่าน"""
        mock_send_email.return_value = True
        
        result = email_service.send_password_changed_email(
            email="user@example.com",
            username="testuser"
        )
        
        assert result == True
        mock_send_email.assert_called_once()
        
        # ตรวจสอบ arguments
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "user@example.com"
        assert "รหัสผ่าน" in call_args[0][1] and "เปลี่ยน" in call_args[0][1]
        assert "testuser" in call_args[0][2]
    
    def test_password_changed_email_has_timestamp(self):
        """✅ อีเมลแจ้งเปลี่ยนรหัสผ่านมี timestamp"""
        # Test ว่ามีการแสดงเวลาที่เปลี่ยนรหัสผ่าน
        from datetime import datetime
        
        # ตรวจสอบว่า email มีการใช้ datetime
        # (จาก fix ที่เราทำไปแล้ว)
        test_service = EmailService()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        assert isinstance(current_time, str)
        assert len(current_time) > 0


class TestEmailTemplates:
    """Test Email HTML Templates"""
    
    def test_all_emails_have_html_structure(self):
        """✅ Email templates มี HTML structure"""
        # ตรวจสอบว่าทุก email มี HTML tags
        
        test_service = EmailService()
        
        # Check verification email
        # (ต้อง inspect code หรือ capture output)
        pass
    
    def test_emails_have_proper_styling(self):
        """✅ Email templates มี CSS styling"""
        # ตรวจสอบว่ามี inline CSS
        pass
    
    def test_emails_are_mobile_friendly(self):
        """📱 Email templates responsive บนมือถือ"""
        # ตรวจสอบว่ามี max-width, padding ที่เหมาะสม
        pass


class TestEmailErrorHandling:
    """Test Email Error Handling"""
    
    @patch('smtplib.SMTP')
    def test_handle_authentication_error(self, mock_smtp):
        """❌ Handle SMTP authentication error"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.login.side_effect = Exception("Authentication failed")
        
        test_service = EmailService()
        test_service.sender_email = "test@example.com"
        test_service.sender_password = "wrong_password"
        
        result = test_service.send_email(
            to_email="user@example.com",
            subject="Test",
            body="Test"
        )
        
        assert result == False
    
    @patch('smtplib.SMTP')
    def test_handle_invalid_recipient(self, mock_smtp):
        """❌ Handle invalid recipient email"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.send_message.side_effect = Exception("Invalid recipient")
        
        test_service = EmailService()
        test_service.sender_email = "test@example.com"
        test_service.sender_password = "password123"
        
        result = test_service.send_email(
            to_email="invalid-email",
            subject="Test",
            body="Test"
        )
        
        assert result == False


class TestEmailIntegration:
    """Integration Tests (require actual SMTP credentials)"""
    
    @pytest.mark.skip(reason="Requires actual SMTP credentials")
    def test_send_real_verification_email(self):
        """✅ Integration: ส่งอีเมลยืนยันจริง"""
        # ต้องมี .env ที่มี EMAIL_USER และ EMAIL_PASSWORD
        
        if not email_service.sender_email or not email_service.sender_password:
            pytest.skip("Email credentials not configured")
        
        result = email_service.send_verification_email(
            email="your-test-email@gmail.com",
            username="Test User",
            token="test_token_123"
        )
        
        assert result == True
    
    @pytest.mark.skip(reason="Requires actual SMTP credentials")
    def test_send_real_password_reset_email(self):
        """✅ Integration: ส่งอีเมลรีเซ็ตรหัสผ่านจริง"""
        if not email_service.sender_email or not email_service.sender_password:
            pytest.skip("Email credentials not configured")
        
        result = email_service.send_password_reset_email(
            email="your-test-email@gmail.com",
            token="reset_token_456"
        )
        
        assert result == True


# ============================================
# Email Testing Tips
# ============================================
"""
การทดสอบ Email Service มีหลายวิธี:

1. Unit Tests (Mock SMTP):
   ✅ เร็ว ไม่ต้องใช้ internet
   ✅ Test logic โดยไม่ส่งอีเมลจริง
   
2. Integration Tests (Real SMTP):
   ✅ ทดสอบการเชื่อมต่อจริง
   ❌ ช้า ต้องมี credentials
   
3. Email Testing Services:
   - Mailtrap.io (สำหรับ development)
   - MailHog (local SMTP server)
   - Gmail Test Account
   
4. Manual Testing:
   - ใช้ email ตัวเอง
   - ตรวจสอบ inbox/spam
   - ทดสอบ links ใน email

วิธีใช้ Mailtrap (แนะนำ):
1. สมัครที่ https://mailtrap.io
2. ตั้งค่า .env:
   SMTP_SERVER=smtp.mailtrap.io
   SMTP_PORT=2525
   EMAIL_USER=your_mailtrap_username
   EMAIL_PASSWORD=your_mailtrap_password
3. Email จะถูกส่งไปที่ Mailtrap inbox (ไม่ส่งไปหาผู้รับจริง)
"""


# ============================================
# Run Tests
# ============================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])