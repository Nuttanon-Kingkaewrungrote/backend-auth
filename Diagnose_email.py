#!/usr/bin/env python3
"""
🔍 Email Troubleshooting Script
ตรวจสอบปัญหา email configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*60)
print("🔍 EMAIL CONFIGURATION DIAGNOSIS")
print("="*60)

# ดึงค่าจาก .env
smtp_server = os.getenv('SMTP_SERVER', '')
smtp_port = os.getenv('SMTP_PORT', '')
email_user = os.getenv('EMAIL_USER', '')
email_password = os.getenv('EMAIL_PASSWORD', '')

print("\n1. ข้อมูลใน .env file:")
print(f"   SMTP_SERVER = {smtp_server or '❌ ไม่มี'}")
print(f"   SMTP_PORT = {smtp_port or '❌ ไม่มี'}")
print(f"   EMAIL_USER = {email_user or '❌ ไม่มี'}")
print(f"   EMAIL_PASSWORD = {'***' + email_password[-4:] if email_password else '❌ ไม่มี'}")

# ตรวจสอบปัญหา
print("\n2. การตรวจสอบ:")

issues = []

# ตรวจสอบว่ามีค่าไหม
if not email_user:
    issues.append("❌ EMAIL_USER ไม่ได้ตั้งค่า")
if not email_password:
    issues.append("❌ EMAIL_PASSWORD ไม่ได้ตั้งค่า")

# ถ้าใช้ Gmail
if 'gmail' in smtp_server.lower():
    print("   📧 ตรวจพบว่าใช้ Gmail")
    
    # ตรวจสอบ password format
    if email_password:
        # App Password ต้องไม่มี space
        if ' ' in email_password:
            issues.append("⚠️  EMAIL_PASSWORD มี space (ต้องเอา space ออก)")
            print(f"      ปัจจุบัน: '{email_password}'")
            print(f"      ควรเป็น: '{email_password.replace(' ', '')}'")
        
        # App Password ควรยาว 16 ตัว
        clean_password = email_password.replace(' ', '')
        if len(clean_password) != 16:
            issues.append(f"⚠️  EMAIL_PASSWORD ยาว {len(clean_password)} ตัว (App Password ควรยาว 16 ตัว)")
        
        # ตรวจสอบว่าเป็น App Password หรือ Gmail password ธรรมดา
        if '@' in email_user and len(clean_password) < 16:
            issues.append("❌ คุณอาจใช้ Gmail password ธรรมดา (ต้องใช้ App Password)")
    
    if not issues:
        print("   ✅ รูปแบบ App Password ถูกต้อง")

# ถ้าใช้ Mailtrap
elif 'mailtrap' in smtp_server.lower():
    print("   📧 ตรวจพบว่าใช้ Mailtrap")
    if not issues:
        print("   ✅ Configuration ดูถูกต้อง")

print("\n3. สรุปปัญหา:")
if issues:
    for issue in issues:
        print(f"   {issue}")
else:
    print("   ✅ ไม่พบปัญหาเบื้องต้น")

print("\n" + "="*60)

# คำแนะนำ
if 'gmail' in smtp_server.lower():
    print("\n💡 วิธีแก้ไข (Gmail):")
    print("\n1. ตรวจสอบว่าคุณใช้ App Password หรือยัง")
    print("   ✅ ถูกต้อง: App Password (16 ตัวอักษร)")
    print("   ❌ ผิด: Gmail password ธรรมดา")
    
    print("\n2. สร้าง App Password:")
    print("   - ไปที่: https://myaccount.google.com/apppasswords")
    print("   - ต้องเปิด 2-Step Verification ก่อน")
    print("   - เลือก App: Mail")
    print("   - เลือก Device: Other → พิมพ์ 'Fund Dashboard'")
    print("   - คัดลอก password 16 ตัว (เช่น: abcd efgh ijkl mnop)")
    
    print("\n3. แก้ไข .env:")
    print("   EMAIL_USER=your-email@gmail.com")
    print("   EMAIL_PASSWORD=abcdefghijklmnop  # เอา space ออก!")
    
    print("\n4. ทดสอบใหม่:")
    print("   python config.py check")

elif 'mailtrap' in smtp_server.lower():
    print("\n💡 วิธีแก้ไข (Mailtrap):")
    print("\n1. ไปที่: https://mailtrap.io/inboxes")
    print("2. เลือก inbox ของคุณ")
    print("3. คลิก 'SMTP Settings' → 'Show Credentials'")
    print("4. คัดลอก Username และ Password")
    print("5. แก้ .env ให้ตรงกับที่คัดลอก")

else:
    print("\n💡 แนะนำ:")
    print("   ลองใช้ Mailtrap แทน Gmail (ง่ายกว่า)")
    print("   1. สมัครที่: https://mailtrap.io")
    print("   2. คัดลอก SMTP credentials")
    print("   3. ใส่ใน .env")

print("\n" + "="*60 + "\n")