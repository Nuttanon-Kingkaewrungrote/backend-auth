# Fund Dashboard Authentication API

REST API สำหรับระบบ Login/Authentication ด้วย FastAPI + MySQL

## Features
- ✅ Register/Login (Username/Password)
- ✅ Login with Google OAuth (Coming Soon)
- ✅ JWT Token Authentication
- ✅ Remember Me (30 days)
- ✅ Forgot/Reset Password
- ✅ Email Verification
- ✅ Change Password
- ✅ Delete Account
- ✅ Rate Limiting (5 login/min)
- ✅ Auto API Documentation (Swagger)

## Tech Stack
- **Backend:** FastAPI 0.104+
- **Database:** MySQL 8.0
- **Authentication:** JWT (PyJWT)
- **Password:** bcrypt
- **Rate Limit:** SlowAPI

## Installation

### 1. Clone Repository
```bash
git clone <your-repo>
cd backend-auth
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Database
```bash
mysql -u root -p < schema.sql
```

### 5. Configure Environment
```bash
cp .env.example .env
# แก้ไข .env ให้ตรงกับ MySQL ของคุณ
```

### 6. Run Server
```bash
python main.py
```

Server จะรันที่: http://localhost:8000
API Docs: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | - | Health check |
| `/api/auth/register` | POST | - | สมัครสมาชิก |
| `/api/auth/login` | POST | - | เข้าสู่ระบบ |
| `/api/auth/verify` | GET | 🔒 | ตรวจสอบ token |
| `/api/auth/logout` | POST | - | ออกจากระบบ |
| `/api/auth/forgot-password` | POST | - | ลืมรหัสผ่าน |
| `/api/auth/reset-password` | POST | - | รีเซ็ตรหัสผ่าน |
| `/api/auth/verify-email` | POST | - | ยืนยันอีเมล |
| `/api/auth/profile` | GET | 🔒 | ดูข้อมูลผู้ใช้ |
| `/api/auth/refresh` | POST | 🔒 | ต่ออายุ token |
| `/api/auth/change-password` | POST | 🔒 | เปลี่ยนรหัสผ่าน |
| `/api/auth/delete-account` | DELETE | 🔒 | ลบบัญชี |

🔒 = ต้องใช้ Token (Authorization: Bearer <token>)

## Testing

### Run All Tests
```bash
pytest test_auth.py -v
```

### Run with Coverage
```bash
pytest test_auth.py -v --cov=main --cov-report=html
```

### Test Specific Class
```bash
pytest test_auth.py::TestLogin -v
```

## Environment Variables
```env
SECRET_KEY=your-secret-key-change-this
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=fund_dashboard
```

## License
MIT