# Authentication API Documentation

## Base URL
```
http://localhost:5000
```

## Endpoints

### 1. Health Check
**GET** `/`

ตรวจสอบว่า API ทำงาน

**Response:**
```json
{
    "message": "API is running!",
    "status": "OK"
}
```

---

### 2. Register (สร้างผู้ใช้)
**POST** `/api/auth/register`

**Request Body:**
```json
{
    "username": "string",
    "password": "string",
    "email": "string" (optional)
}
```

**Response (201 Created):**
```json
{
    "message": "User created successfully"
}
```

**Error Responses:**
- 400: Missing username or password
- 409: Username already exists

---

### 3. Login (เข้าสู่ระบบ)
**POST** `/api/auth/login`

**Request Body:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response (200 OK):**
```json
{
    "token": "eyJ0eXAiOiJKV1Qi...",
    "user": {
        "id": 1,
        "username": "testuser",
        "role": "user"
    }
}
```

**Error Responses:**
- 400: Missing credentials
- 401: Invalid username or password

---

### 4. Verify Token (ตรวจสอบ Token)
**GET** `/api/auth/verify`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
    "valid": true,
    "user": {
        "user_id": 1,
        "username": "testuser",
        "role": "user",
        "exp": 1769504094
    }
}
```

**Error Responses:**
- 401: No token provided / Token expired / Invalid token

---

### 5. Logout (ออกจากระบบ)
**POST** `/api/auth/logout`

**Response (200 OK):**
```json
{
    "message": "Logged out successfully"
}
```

---

## Security

- Password เข้ารหัสด้วย **bcrypt**
- JWT Token มีอายุ **24 ชั่วโมง**
- Secret Key: ควรเปลี่ยนใน production

---

## Database Schema

**Table: users**
| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary Key, Auto Increment |
| username | VARCHAR(50) | Unique, ชื่อผู้ใช้ |
| password_hash | VARCHAR(255) | รหัสผ่านที่เข้ารหัส |
| email | VARCHAR(100) | อีเมล |
| role | ENUM('admin','user') | บทบาท |
| created_at | TIMESTAMP | วันที่สร้าง |
| last_login | TIMESTAMP | Login ครั้งล่าสุด |

---

## ตัวอย่างการใช้งาน (Postman)

### Login Flow:
1. Register → สร้าง user
2. Login → ได้ token
3. Verify → ตรวจสอบ token
4. Logout

---

## Notes สำหรับ Frontend Team

- ทุก POST request ต้องส่ง `Content-Type: application/json`
- Token ต้องส่งใน Header: `Authorization: Bearer <token>`
- Token หมดอายุ 24 ชม. ต้อง Login ใหม่