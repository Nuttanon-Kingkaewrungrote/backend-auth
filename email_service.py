import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta

load_dotenv()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('EMAIL_USER')
        self.sender_password = os.getenv('EMAIL_PASSWORD')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')
        
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """ส่งอีเมลผ่าน SMTP"""
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured. Skipping email send.")
            return False
            
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.sender_email
            message["To"] = to_email
            message["Subject"] = subject
            
            html_part = MIMEText(body, "html")
            message.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_verification_email(self, email: str, username: str, token: str) -> bool:
        """ส่งอีเมลยืนยัน"""
        verify_link = f"{self.frontend_url}/verify-email?token={token}"
        
        subject = "ยืนยันอีเมลของคุณ - Fund Dashboard"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Fund Dashboard</h1>
                </div>
                <div class="content">
                    <h2>สวัสดี {username}!</h2>
                    <p>ขอบคุณที่สมัครสมาชิกกับเรา กรุณายืนยันอีเมลของคุณโดยคลิกปุ่มด้านล่าง:</p>
                    <a href="{verify_link}" class="button">ยืนยันอีเมล</a>
                    <p>หรือคัดลอกลิงก์นี้:</p>
                    <p style="word-break: break-all; color: #666;">{verify_link}</p>
                    <p style="margin-top: 30px; color: #666;">หากคุณไม่ได้สมัครสมาชิก กรุณาเพิกเฉยอีเมลนี้</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Fund Dashboard. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, body)
    
    def send_password_reset_email(self, email: str, token: str) -> bool:
        """ส่งอีเมลรีเซ็ตรหัสผ่าน"""
        reset_link = f"{self.frontend_url}/reset-password?token={token}"
        
        subject = "รีเซ็ตรหัสผ่านของคุณ - Fund Dashboard"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #EF4444; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #EF4444; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background: #FEF3C7; padding: 15px; border-left: 4px solid #F59E0B; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>รีเซ็ตรหัสผ่าน</h1>
                </div>
                <div class="content">
                    <p>เราได้รับคำขอรีเซ็ตรหัสผ่านสำหรับบัญชีของคุณ</p>
                    <p>กรุณากดปุ่มด้านล่างเพื่อตั้งรหัสผ่านใหม่:</p>
                    <a href="{reset_link}" class="button">รีเซ็ตรหัสผ่าน</a>
                    <p>หรือคัดลอกลิงก์นี้:</p>
                    <p style="word-break: break-all; color: #666;">{reset_link}</p>
                    <div class="warning">
                        <strong>⚠️ คำเตือน:</strong> ลิงก์นี้จะหมดอายุใน <strong>1 ชั่วโมง</strong>
                    </div>
                    <p style="color: #666;">หากคุณไม่ได้ขอรีเซ็ตรหัสผ่าน กรุณาเพิกเฉยอีเมลนี้ รหัสผ่านของคุณจะไม่เปลี่ยนแปลง</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Fund Dashboard. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, body)
    
    def send_password_changed_email(self, email: str, username: str) -> bool:
        """ส่งอีเมลแจ้งเตือนเปลี่ยนรหัสผ่าน"""
        # แก้ไข: คำนวณ current_time ก่อนใช้ใน f-string
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        subject = "รหัสผ่านของคุณถูกเปลี่ยนแปลง - Fund Dashboard"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #10B981; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .alert {{ background: #FEE2E2; padding: 15px; border-left: 4px solid #EF4444; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>รหัสผ่านถูกเปลี่ยน</h1>
                </div>
                <div class="content">
                    <h2>สวัสดี {username}!</h2>
                    <p>รหัสผ่านของคุณถูกเปลี่ยนเรียบร้อยแล้ว</p>
                    <p>เวลา: {current_time}</p>
                    <div class="alert">
                        <strong>⚠️ หากไม่ใช่คุณที่เปลี่ยน:</strong><br>
                        กรุณารีเซ็ตรหัสผ่านของคุณทันทีและติดต่อฝ่ายสนับสนุน
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Fund Dashboard. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, body)

# สร้าง instance
email_service = EmailService()