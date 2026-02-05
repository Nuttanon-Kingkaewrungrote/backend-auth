#!/usr/bin/env python3
"""
Helper: ทดสอบ reset password ด้วย token
"""

import sys
import requests

if len(sys.argv) < 3:
    print("Usage: python reset_password.py <token> <new-password>")
    print("\nตัวอย่าง:")
    print("  python reset_password.py abc123def456... mynewpassword123")
    sys.exit(1)

token = sys.argv[1]
new_password = sys.argv[2]

print(f"\n🔍 กำลังรีเซ็ตรหัสผ่านด้วย token: {token[:20]}...")
print(f"   รหัสผ่านใหม่: {new_password}")

try:
    response = requests.post(
        "http://localhost:8000/api/auth/reset-password",
        json={
            "token": token,
            "new_password": new_password
        }
    )
    
    result = response.json()
    
    if response.status_code == 200 and "message" in result:
        print(f"✅ {result['message']}")
        print("\n   สามารถ login ด้วยรหัสผ่านใหม่ได้แล้ว!")
    else:
        print(f"❌ Error: {result}")
        
except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")
