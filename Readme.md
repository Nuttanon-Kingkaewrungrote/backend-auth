# 🚀 IdeaTradeFund Auth System — คู่มือ Deploy บน VM

---

## 📋 สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [โครงสร้างไฟล์](#2-โครงสร้างไฟล์)
3. [ติดตั้ง VM](#3-ติดตั้ง-vm-ubuntu)
4. [ตั้งค่า Database](#4-ตั้งค่า-database)
5. [สร้างไฟล์ .env](#5-สร้างไฟล์-env)
6. [⚠️ ทุกจุดที่ต้องเปลี่ยน URL](#6-️-ทุกจุดที่ต้องเปลี่ยน-url)
7. [ตั้งค่า Google Cloud Console](#7-ตั้งค่า-google-cloud-console)
8. [รัน Backend (systemd + Nginx + SSL)](#8-รัน-backend)
9. [ตั้งค่า WordPress](#9-ตั้งค่า-wordpress)
10. [ทดสอบระบบ](#10-ทดสอบระบบ)
11. [API Endpoints](#11-api-endpoints)
12. [Troubleshooting](#12-troubleshooting)
13. [Checklist](#13-checklist-ก่อน-go-live)

---

## 1. ภาพรวมระบบ

```
┌──────────────────────────────┐
│  WordPress (ideatradefund.com)│
│  ┌────────────────────────┐  │
│  │ wordpress_snippet.php  │  │
│  │  ● Login / Register    │  │
│  │  ● Navbar + Avatar     │  │
│  │  ● Profile page        │  │
│  │  ● Google login popup  │  │
│  └──────────┬─────────────┘  │
└─────────────┼────────────────┘
              │ HTTPS (FUND_BACKEND)
              ▼
┌──────────────────────────────┐
│  VM Backend (FastAPI :8000)   │
│  ┌────────────────────────┐  │
│  │ main.py   — Auth core  │  │
│  │ oauth.py  — Google SSO │  │
│  │ email_service.py       │  │
│  │ Config.py — Validation │  │
│  │ Auth_middleware.py      │  │
│  └──────────┬─────────────┘  │
└─────────────┼────────────────┘
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
 MySQL    Google API  Gmail SMTP
```

**Features:**
- Login (email/username + password)
- Login ด้วย Google (One Tap popup)
- สมัครสมาชิก + ยืนยัน email
- ลืม/รีเซ็ตรหัสผ่าน (ส่ง email)
- Profile: เปลี่ยนชื่อ, อัพโหลด avatar, เปลี่ยน password
- เชื่อม/ยกเลิกเชื่อม Google account
- Navbar: แสดงรูป + ชื่อ user + dropdown menu

---

## 2. โครงสร้างไฟล์

```
backend-auth/
│
├── main.py                    # FastAPI app หลัก
├── oauth.py                   # Google OAuth endpoints
├── email_service.py           # ส่ง email (verify, reset, notification)
├── Config.py                  # Config validation + security settings
├── Auth_middleware.py          # JWT middleware สำหรับ service อื่น
├── verify_token.py            # Helper: ทดสอบ verify email token
├── Diagnose_email.py          # Helper: ตรวจสอบ email config
├── requirements.txt           # Python packages (pinned versions)
├── .env.example               # ตัวอย่าง environment variables
├── .gitignore                 # Git ignore rules
│
├── Database/
│   ├── deploy_database.sql    # สร้าง DB + tables + triggers + views
│   └── rollback_database.sql  # ลบทุกอย่าง (ใช้ตอนต้องการ reset)
│
├── Tests/
│   ├── test_auth.py           # Unit tests — auth endpoints
│   ├── test_oauth.py          # Unit tests — Google OAuth
│   └── test_flows.py          # E2E tests — email flows
│
├── WordPress/
│   └── wordpress_snippet.php  # Code Snippet สำหรับ WordPress
│
├── uploads/                   # สร้างอัตโนมัติ
│   └── avatars/               # เก็บรูป profile
│
└── logs/                      # สร้างอัตโนมัติ
    └── app_YYYYMMDD.log       # Application logs
```

---

## 3. ติดตั้ง VM (Ubuntu)

```bash
# 1. Update
sudo apt update && sudo apt upgrade -y

# 2. Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# 3. MySQL
sudo apt install mysql-server -y
sudo systemctl enable mysql

# 4. Nginx + Certbot (SSL)
sudo apt install nginx certbot python3-certbot-nginx -y

# 5. สร้างโฟลเดอร์โปรเจค
sudo mkdir -p /opt/fundauth
cd /opt/fundauth

# 6. วางไฟล์ทั้งหมดจาก repo
#    main.py, oauth.py, email_service.py, Config.py,
#    Auth_middleware.py, requirements.txt
#    Database/deploy_database.sql

# 7. สร้าง venv + ติดตั้ง packages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 4. ตั้งค่า Database

### 4.1 สร้าง MySQL User

```bash
sudo mysql
```

```sql
-- สร้าง user (⚠️ เปลี่ยน password)
CREATE USER 'funduser'@'localhost' IDENTIFIED BY 'เปลี่ยน_PASSWORD_ตรงนี้';
GRANT ALL PRIVILEGES ON fund_dashboard.* TO 'funduser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4.2 รัน deploy_database.sql

```bash
mysql -u funduser -p < Database/deploy_database.sql
```

**สิ่งที่ script นี้ทำ:**
- สร้าง database `fund_dashboard`
- สร้างตาราง `users` (พร้อม display_name, avatar_url, email verification, password reset)
- สร้างตาราง `oauth_accounts` (Google link)
- สร้าง stored procedures, views, triggers
- สร้าง admin user เริ่มต้น (username: `admin`, password: `admin123`)

### 4.3 เช็คว่าสำเร็จ

```bash
mysql -u funduser -p fund_dashboard -e "SHOW TABLES;"
# ควรเห็น: users, oauth_accounts
```

### หมายเหตุ: Rollback

ถ้าต้องการลบทุกอย่างแล้วเริ่มใหม่:
```bash
mysql -u funduser -p fund_dashboard < Database/rollback_database.sql
```

---

## 5. สร้างไฟล์ .env

คัดลอกจาก `.env.example` แล้วแก้ค่า:

```bash
cp .env.example .env
nano .env
```

```env
# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
DB_HOST=localhost
DB_USER=funduser
DB_PASSWORD=เปลี่ยน_PASSWORD_ตรงนี้          # ⚠️ เปลี่ยน
DB_NAME=fund_dashboard

# ═══════════════════════════════════════
# JWT SECRET
# ═══════════════════════════════════════
SECRET_KEY=เปลี่ยน_SECRET_ตรงนี้              # ⚠️ เปลี่ยน

# ═══════════════════════════════════════
# GOOGLE OAUTH (จาก Google Cloud Console)
# ═══════════════════════════════════════
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=https://api.example.com/api/auth/google/callback  # ⚠️ domain VM

# ═══════════════════════════════════════
# WORDPRESS
# ═══════════════════════════════════════
WP_SITE_URL=https://ideatradefund.com
FRONTEND_URL=https://api.example.com         # ⚠️ domain VM

# ═══════════════════════════════════════
# EMAIL (ชื่อตัวแปรต้องตรงตามนี้!)
# ═══════════════════════════════════════
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your-email@gmail.com              # ⚠️ เปลี่ยน
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx           # ⚠️ Gmail App Password

# ═══════════════════════════════════════
# ENVIRONMENT
# ═══════════════════════════════════════
ENVIRONMENT=production
DEBUG=False
```

> ⚠️ **สำคัญ:** ชื่อตัวแปร email ต้องเป็น `EMAIL_USER` และ `EMAIL_PASSWORD` (ไม่ใช่ `MAIL_USERNAME`) เพราะ `email_service.py` อ่านชื่อนี้

**สร้าง SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**สร้าง Gmail App Password:**
1. ไป [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. ต้องเปิด 2-Step Verification ก่อน
3. สร้าง App Password → คัดลอก 16 ตัว → ใส่ `EMAIL_PASSWORD` (ไม่มี space)

**ตรวจสอบ config:**
```bash
python3 Config.py check
```

---

## 6. ⚠️ ทุกจุดที่ต้องเปลี่ยน URL

> สมมติ:
> - **VM Backend** = `https://api.ideatradefund.com`
> - **WordPress** = `https://ideatradefund.com`

### ตารางรวม — ทุกจุดที่ต้องแก้

| # | ไฟล์ | ตัวแปร/ตำแหน่ง | เปลี่ยนเป็น |
|---|------|---------------|------------|
| 1 | `.env` | `GOOGLE_REDIRECT_URI` | `https://[VM]/api/auth/google/callback` |
| 2 | `.env` | `WP_SITE_URL` | `https://[WordPress]` |
| 3 | `.env` | `FRONTEND_URL` | `https://[VM]` |
| 4 | `.env` | `DB_PASSWORD` | รหัส MySQL |
| 5 | `.env` | `SECRET_KEY` | สุ่มด้วย python |
| 6 | `.env` | `GOOGLE_CLIENT_ID` | จาก Google Console |
| 7 | `.env` | `GOOGLE_CLIENT_SECRET` | จาก Google Console |
| 8 | `.env` | `EMAIL_USER` | Gmail address |
| 9 | `.env` | `EMAIL_PASSWORD` | Gmail App Password |
| 10 | `main.py` บรรทัด ~90 | `allow_origins` | เพิ่ม `https://[WordPress]` |
| 11 | `Config.py` บรรทัด ~177 | `get_cors_origins()` production | เปลี่ยน `yourdomain.com` → `[WordPress]` |
| 12 | `wordpress_snippet.php` บรรทัด 15 | `FUND_BACKEND` | `https://[VM]` |
| 13 | Google Cloud Console | Authorized JS origins | `https://[WordPress]` |
| 14 | Google Cloud Console | Authorized redirect URIs | `https://[VM]/api/auth/google/callback` |

> `[VM]` = domain backend เช่น `api.ideatradefund.com`
> `[WordPress]` = domain เว็บ เช่น `ideatradefund.com`

---

### รายละเอียดทีละจุด

#### จุดที่ 1-9: `.env`

ดู [หัวข้อ 5](#5-สร้างไฟล์-env)

#### จุดที่ 10: `main.py` — CORS (บรรทัด ~90)

```python
allow_origins=[
    "https://ideatradefund.com",         # ⚠️ domain WordPress
    "https://www.ideatradefund.com",      # ⚠️ www version
    "http://localhost",
],
```

> ถ้าไม่เพิ่ม → browser จะ block ทุก API call จาก WordPress!

#### จุดที่ 11: `Config.py` — SecurityConfig (บรรทัด ~177)

```python
if env == 'production':
    return [
        "https://ideatradefund.com",      # ⚠️ เปลี่ยน
        "https://www.ideatradefund.com",   # ⚠️ เปลี่ยน
    ]
```

#### จุดที่ 12: `wordpress_snippet.php` (บรรทัด 15)

```php
define('FUND_BACKEND', 'https://api.ideatradefund.com');  // ⚠️ domain VM
```

> จุดเดียวที่ต้องแก้ใน WordPress

#### จุดที่ 13-14: Google Cloud Console

ดู [หัวข้อ 7](#7-ตั้งค่า-google-cloud-console)

---

## 7. ตั้งค่า Google Cloud Console

1. ไปที่ [console.cloud.google.com](https://console.cloud.google.com)
2. **APIs & Services** → **Credentials**
3. สร้าง/แก้ **OAuth 2.0 Client ID** (Type: Web application)

```
Authorized JavaScript origins:
  ✅ https://ideatradefund.com

Authorized redirect URIs:
  ✅ https://api.ideatradefund.com/api/auth/google/callback
```

4. คัดลอก **Client ID** + **Client Secret** → ใส่ `.env`

> ⚠️ URL ต้องตรง **ทุกตัวอักษร** กับ `.env` → `GOOGLE_REDIRECT_URI`
> (ไม่มี `/` ต่อท้าย, `https` ไม่ใช่ `http`)

---

## 8. รัน Backend

### 8.1 ทดสอบก่อน (foreground)

```bash
cd /opt/fundauth
source venv/Scripts/activate
python3 Config.py check    # ตรวจสอบ config
python3 main.py            # รัน server
# เปิด http://localhost:8000/health
```

### 8.2 สร้าง systemd service

```bash
sudo nano /etc/systemd/system/fundauth.service
```

```ini
[Unit]
Description=FundAuth FastAPI Backend
After=network.target mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/fundauth
EnvironmentFile=/opt/fundauth/.env
ExecStart=/opt/fundauth/venv/bin/python3 main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo chown -R www-data:www-data /opt/fundauth
sudo chmod 600 /opt/fundauth/.env

sudo systemctl daemon-reload
sudo systemctl enable fundauth
sudo systemctl start fundauth
sudo systemctl status fundauth
```

### 8.3 Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/fundauth
```

```nginx
server {
    listen 80;
    server_name api.ideatradefund.com;    # ⚠️ เปลี่ยน domain

    client_max_body_size 5M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/fundauth /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL ฟรี
sudo certbot --nginx -d api.ideatradefund.com
```

### 8.4 Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 9. ตั้งค่า WordPress

### 9.1 เพิ่ม Code Snippet

1. WPCode / Code Snippets plugin
2. สร้าง PHP Snippet → วาง code จาก `wordpress_snippet.php`
3. **⚠️ แก้บรรทัด 15:**
   ```php
   define('FUND_BACKEND', 'https://api.ideatradefund.com');
   ```
4. Activate

### 9.2 หน้าที่ต้องมี

| หน้า | Slug | เนื้อหา |
|------|------|---------|
| เข้าสู่ระบบ | `เข้าสู่ระบบ` | GreenShift form (email + password) |
| สมัครสมาชิก | `สมัครสมาชิก` | GreenShift form (email + username + password + confirm) |
| โปรไฟล์ | `profile` | Custom HTML block (profile_layout.html) |
| ลืมรหัสผ่าน | `forgot-password` | GreenShift form (email) |
| รีเซ็ตรหัสผ่าน | `reset-password` | GreenShift form (password + confirm) |

### 9.3 Navbar

ต้องมีปุ่ม `เข้าสู่ระบบ` ใน navbar — Snippet จะแทนที่ด้วย avatar + dropdown อัตโนมัติเมื่อ login

---

## 10. ทดสอบระบบ

### 10.1 Health Check
```bash
curl https://api.ideatradefund.com/health
# {"status":"healthy","database":"connected",...}
```

### 10.2 Config Check
```bash
cd /opt/fundauth && source venv/bin/activate
python3 Config.py check
```

### 10.3 Email Check
```bash
python3 Diagnose_email.py
```

### 10.4 API Docs
เปิด browser: `https://api.ideatradefund.com/docs`

### 10.5 Run Tests
```bash
pytest test_auth.py -v
```

### 10.6 ทดสอบผ่าน WordPress

1. **Login:** เปิดหน้าเข้าสู่ระบบ → กรอก email + password → ควรเห็น "ยินดีต้อนรับ"
2. **Google Login:** กดปุ่ม Google → popup → เลือก account → login สำเร็จ
3. **Register:** สมัครสมาชิก → ควรสร้าง user + ส่ง verification email
4. **Profile:** ไปหน้า profile → แก้ชื่อ / upload รูป / Link Google
5. **Forgot Password:** กรอก email → ควรได้ email reset link

---

## 11. API Endpoints

### Public

| Method | Endpoint | คำอธิบาย |
|--------|----------|---------|
| GET | `/health` | Health check + DB status |
| GET | `/` | API info |
| POST | `/api/auth/register` | สมัครสมาชิก |
| POST | `/api/auth/login` | เข้าสู่ระบบ |
| POST | `/api/auth/forgot-password` | ขอ reset password |
| POST | `/api/auth/reset-password` | Reset ด้วย token |
| POST | `/api/auth/verify-email` | Verify email token |
| GET | `/api/auth/google/url` | ดึง Google OAuth URL |
| GET | `/api/auth/google/callback` | Google redirect callback |
| POST | `/api/auth/google/verify` | Verify Google ID token (popup) |

### Protected (ต้องส่ง `Authorization: Bearer <token>`)

| Method | Endpoint | คำอธิบาย |
|--------|----------|---------|
| GET | `/api/auth/verify` | ตรวจสอบ token |
| GET | `/api/auth/account-info` | ข้อมูล user + linked accounts |
| POST | `/api/auth/change-password` | เปลี่ยนรหัสผ่าน |
| POST | `/api/auth/set-password` | ตั้งรหัสผ่าน (OAuth-only user) |
| POST | `/api/auth/update-profile` | เปลี่ยน display_name |
| POST | `/api/auth/upload-avatar` | อัพโหลดรูป (max 2MB) |
| POST | `/api/auth/link-google` | เชื่อม Google account |
| GET | `/api/auth/linked-accounts` | ดู accounts ที่เชื่อม |
| DELETE | `/api/auth/unlink/google` | ยกเลิกเชื่อม Google |
| POST | `/api/auth/refresh` | Refresh token |
| DELETE | `/api/auth/delete-account` | ลบบัญชี |

---

## 12. Troubleshooting

### ❌ CORS Error
```
Access to XMLHttpRequest has been blocked by CORS policy
```
**แก้:** `main.py` บรรทัด ~90 → เพิ่ม WordPress domain ใน `allow_origins`

### ❌ Google: redirect_uri_mismatch
**แก้:** URL ใน Google Console ต้องตรงกับ `.env` → `GOOGLE_REDIRECT_URI` ทุกตัวอักษร

### ❌ ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้
```bash
sudo systemctl status fundauth    # Backend รัน?
sudo systemctl status nginx        # Nginx ทำงาน?
curl http://127.0.0.1:8000/health  # API ตอบ?
sudo ufw status                    # Firewall?
```

### ❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้
```bash
sudo systemctl status mysql
mysql -u funduser -p fund_dashboard -e "SELECT 1;"
```

### ❌ Email ส่งไม่ได้
```bash
python3 Diagnose_email.py          # ตรวจสอบ config
# ต้องใช้ Gmail App Password (ไม่ใช่รหัสปกติ)
# ชื่อตัวแปร: EMAIL_USER + EMAIL_PASSWORD (ไม่ใช่ MAIL_USERNAME)
```

### ❌ Avatar ไม่แสดง
```bash
sudo chown -R www-data:www-data /opt/fundauth/uploads
sudo chmod -R 755 /opt/fundauth/uploads
```

### 📋 ดู Logs
```bash
sudo journalctl -u fundauth -f                # systemd log (realtime)
tail -f /opt/fundauth/logs/app_*.log           # application log
sudo tail -f /var/log/nginx/error.log          # nginx log
```

---

## 13. Checklist ก่อน Go Live

### VM
- [ ] Python + venv + `pip install -r requirements.txt`
- [ ] MySQL + user + `deploy_database.sql`
- [ ] `.env` — ค่าครบทุกตัว
- [ ] `python3 Config.py check` → ผ่าน
- [ ] `main.py` CORS origins → มี domain WordPress
- [ ] `Config.py` production origins → มี domain WordPress
- [ ] systemd service → enabled + running
- [ ] Nginx → reverse proxy + SSL
- [ ] Firewall → port 80, 443
- [ ] `curl /health` → `{"status":"healthy"}`

### Google Cloud Console
- [ ] JS origins = `https://ideatradefund.com`
- [ ] redirect URIs = `https://[VM]/api/auth/google/callback`

### WordPress
- [ ] `FUND_BACKEND` → ชี้ไป VM domain
- [ ] Snippet → Activated
- [ ] หน้า Profile → Published

### ทดสอบ
- [ ] Login ปกติ ✅
- [ ] Google Login ✅
- [ ] Register ✅
- [ ] Profile (แก้ชื่อ/รูป) ✅
- [ ] Forgot Password (ส่ง email) ✅
- [ ] Link/Unlink Google ✅