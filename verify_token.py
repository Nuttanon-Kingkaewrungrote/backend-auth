#!/usr/bin/env python3
"""
Helper: ทดสอบ verify email token
"""

import sys
import requests

if len(sys.argv) < 2:
    print("Usage: python verify_token.py <token>")
    print("\nตัวอย่าง:")
    print("  python verify_token.py abc123def456...")
    sys.exit(1)

token = sys.argv[1]

print(f"\n🔍 กำลังทดสอบ verification token: {token[:20]}...")

try:
    response = requests.post(
        "http://localhost:8000/api/auth/verify-email",
        json={"token": token}
    )
    
    result = response.json()
    
    if response.status_code == 200 and "message" in result:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ Error: {result}")
        
except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {e}")
