# Backend Authentication API

ระบบ Login Backend สำหรับ Fund Dashboard

## Requirements

- Python 3.8+
- MySQL 8.0+

## การติดตั้ง

### 1. Clone/Copy โปรเจค

### 2. สร้าง Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 3. ติดตั้ง Dependencies
```bash
pip install flask pymysql bcrypt pyjwt
```

### 4. สร้าง Database
```sql
CREATE DATABASE fund_dashboard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fund_dashboard;

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role ENUM('admin', 'user') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username)
);
```

### 5. แก้ไข app.py
แก้รหัสผ่าน MySQL ในไฟล์ `app.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD',  # แก้ตรงนี้
    'database': 'fund_dashboard'
}
```

### 6. รันโปรแกรม
```bash
python app.py
```

API จะรันที่: http://localhost:5000

## การทดสอบ

ดู API Documentation ใน `API_DOCS.md`

## โครงสร้างโปรเจค
```
backend-auth/
├── venv/              # Virtual environment
├── app.py             # API หลัก
├── API_DOCS.md        # เอกสาร API
└── README.md          # คู่มือนี้
```

## Status

✅ Register API  
✅ Login API  
✅ Verify Token API  
✅ Logout API  
✅ Database Schema  
✅ Security (bcrypt + JWT)  
⏳ รอ Frontend Integration

## Contact

[ชื่อคุณ]  
[อีเมล]

source venv/Scripts/activate    # Git Bash
# หรือ
venv\Scripts\activate           # Command Prompt

# 4. รัน API
python app.py

# 5. ทดสอบ
# เปิด http://localhost:5000
```
pytest test_auth.py -v