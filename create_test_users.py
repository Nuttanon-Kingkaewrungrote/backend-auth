import pymysql
import bcrypt

# แก้รหัสผ่าน MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Root1234',  # แก้ตรงนี้
    'database': 'fund_dashboard'
}

# Test users
test_users = [
    ('admin', 'admin123', 'admin@company.com', 'admin'),
    ('user1', 'pass123', 'user1@company.com', 'user'),
    ('user2', 'pass123', 'user2@company.com', 'user'),
    ('frontend_test', 'test123', 'frontend@company.com', 'user'),
]

try:
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for username, password, email, role in test_users:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                (username, hashed.decode('utf-8'), email, role)
            )
            print(f"✅ Created user: {username}")
        except pymysql.IntegrityError:
            print(f"⚠️  User {username} already exists")
    
    conn.commit()
    conn.close()
    print("\n🎉 Test users created successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")