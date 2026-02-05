#!/usr/bin/env python3
"""
🧪 End-to-End Email Flow Testing
ทดสอบ email flow ทั้งหมด
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_register_with_email():
    """Test 1: Register + Verification Email"""
    print_header("Test 1: Register + Send Verification Email")
    
    data = {
        "username": f"testuser_{int(time.time())}",
        "password": "testpass123",
        "email": input("ใส่ email ของคุณ: ").strip()
    }
    
    print(f"\n📝 กำลังสมัครด้วย username: {data['username']}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
        result = response.json()
        
        if response.status_code == 200 and "message" in result:
            print(f"✅ {result['message']}")
            print(f"\n📧 Email ถูกส่งไปที่: {data['email']}")
            print("   กรุณาเช็ค inbox (หรือ Spam folder)")
            print("\n   ในอีเมลจะมี link แบบนี้:")
            print("   http://localhost:8000/verify-email?token=...")
            print("\n   ให้คัดลอก token จาก link แล้วทดสอบด้วย:")
            print(f"   python verify_token.py <token>")
            
            return data['username']
        else:
            print(f"❌ Error: {result}")
            return None
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return None

def test_forgot_password():
    """Test 2: Forgot Password"""
    print_header("Test 2: Forgot Password + Reset Email")
    
    email = input("ใส่ email ที่ต้องการรีเซ็ตรหัสผ่าน: ").strip()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/forgot-password",
            json={"email": email}
        )
        result = response.json()
        
        if response.status_code == 200:
            print(f"✅ {result['message']}")
            print(f"\n📧 Email ถูกส่งไปที่: {email}")
            print("   กรุณาเช็ค inbox (หรือ Spam folder)")
            print("\n   ในอีเมลจะมี link แบบนี้:")
            print("   http://localhost:8000/reset-password?token=...")
            print("\n   ให้คัดลอก token จาก link แล้วทดสอบด้วย:")
            print("   python reset_password.py <token> <new-password>")
        else:
            print(f"❌ Error: {result}")
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

def test_login_and_change_password():
    """Test 3: Login + Change Password + Notification Email"""
    print_header("Test 3: Change Password + Send Notification")
    
    username = input("ใส่ username: ").strip()
    password = input("ใส่ password: ").strip()
    
    # Login
    print("\n📝 กำลัง login...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": username,
                "password": password,
                "remember_me": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if "token" in data:
                token = data["token"]
                print("✅ Login สำเร็จ!")
                
                # Change Password
                print("\n📝 กำลังเปลี่ยนรหัสผ่าน...")
                new_password = input("ใส่รหัสผ่านใหม่: ").strip()
                
                response2 = requests.post(
                    f"{BASE_URL}/api/auth/change-password",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "current_password": password,
                        "new_password": new_password
                    }
                )
                
                result2 = response2.json()
                
                if response2.status_code == 200:
                    print(f"✅ {result2['message']}")
                    print("\n📧 Notification email ถูกส่งไป!")
                    print("   เช็ค inbox จะเห็น email แจ้งเตือนการเปลี่ยนรหัสผ่าน")
                else:
                    print(f"❌ Error: {result2}")
            else:
                print(f"❌ Login failed: {data}")
        else:
            print(f"❌ Error: {response.json()}")
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

def main():
    print("\n" + "🧪"*30)
    print("  END-TO-END EMAIL TESTING")
    print("🧪"*30)
    
    print("\n⚠️  กรุณาเปิด server ก่อน: python main.py")
    input("กด Enter เมื่อ server เปิดแล้ว...")
    
    # ตรวจสอบว่า server เปิดอยู่หรือไม่
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server พร้อมใช้งาน!\n")
        else:
            print("❌ Server ไม่พร้อม")
            return
    except:
        print("❌ ไม่สามารถเชื่อมต่อ server ได้")
        print("   กรุณาเปิด server ด้วย: python main.py")
        return
    
    while True:
        print("\n" + "="*60)
        print("เลือก Test:")
        print("  1. Register + Verification Email")
        print("  2. Forgot Password + Reset Email")
        print("  3. Change Password + Notification Email")
        print("  4. ออก")
        print("="*60)
        
        choice = input("\nเลือก (1-4): ").strip()
        
        if choice == "1":
            test_register_with_email()
        elif choice == "2":
            test_forgot_password()
        elif choice == "3":
            test_login_and_change_password()
        elif choice == "4":
            print("\n👋 ออกจากโปรแกรม")
            break
        else:
            print("❌ กรุณาเลือก 1-4")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 ออกจากโปรแกรม")
