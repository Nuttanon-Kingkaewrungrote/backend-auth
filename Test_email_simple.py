#!/usr/bin/env python3
"""
🧪 Email Test Script
ทดสอบว่า Email Service ทำงานหรือไม่
"""

import sys
import os

# เพิ่ม path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_service import email_service

def main():
    print("\n" + "="*60)
    print("📧 EMAIL SERVICE TEST")
    print("="*60)
    
    # 1. ตรวจสอบ config
    print("\n1. ตรวจสอบการตั้งค่า...")
    print(f"   SMTP Server: {email_service.smtp_server}")
    print(f"   SMTP Port: {email_service.smtp_port}")
    print(f"   Sender Email: {email_service.sender_email or '❌ ไม่ได้ตั้งค่า'}")
    print(f"   Password: {'✅ มี' if email_service.sender_password else '❌ ไม่มี'}")
    
    if not email_service.is_configured():
        print("\n❌ Email ยังไม่ได้ตั้งค่า!")
        print("\nกรุณาแก้ไขไฟล์ .env:")
        print("   EMAIL_USER=your-email")
        print("   EMAIL_PASSWORD=your-password")
        print("\nดูวิธีตั้งค่าที่: EMAIL_SETUP_SIMPLE.md")
        return
    
    print("\n✅ Email ตั้งค่าแล้ว!\n")
    
    # 2. ถามว่าจะส่งไปที่ไหน
    print("2. ทดสอบส่ง Email")
    to_email = input("   ส่งไปที่ email: ").strip()
    
    if not to_email or '@' not in to_email:
        print("   ❌ Email ไม่ถูกต้อง")
        return
    
    print(f"\n   กำลังส่ง verification email ไปที่ {to_email}...")
    
    # 3. ส่ง email
    result = email_service.send_verification_email(
        email=to_email,
        username="TestUser",
        token="test_verification_token_123"
    )
    
    # 4. แสดงผล
    print("\n" + "="*60)
    if result:
        print("✅ ส่ง Email สำเร็จ!")
        print("\nขั้นตอนต่อไป:")
        
        if 'mailtrap' in email_service.smtp_server:
            print("   1. เปิด https://mailtrap.io")
            print("   2. ไปที่ inbox ของคุณ")
            print("   3. คุณจะเห็น email ที่เพิ่งส่ง!")
        else:
            print(f"   1. เช็ค inbox ของ {to_email}")
            print("   2. ถ้าไม่เจอ ดูใน Spam folder")
    else:
        print("❌ ส่ง Email ไม่สำเร็จ!")
        print("\nสาเหตุที่เป็นไปได้:")
        print("   - EMAIL_USER หรือ EMAIL_PASSWORD ผิด")
        print("   - ถ้าใช้ Gmail ต้องใช้ App Password")
        print("   - ไม่มี internet")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ ยกเลิก")
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")