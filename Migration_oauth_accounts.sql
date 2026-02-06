-- ============================================
-- Quick Migration for Existing Database
-- Run this if you already have fund_dashboard
-- ============================================

USE fund_dashboard;

-- เพิ่มคอลัมน์ที่ขาดใน users
ALTER TABLE users ADD COLUMN has_password BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN oauth_only BOOLEAN DEFAULT FALSE;

-- เพิ่มคอลัมน์ที่ขาดใน oauth_accounts
ALTER TABLE oauth_accounts ADD COLUMN provider_email VARCHAR(255);
ALTER TABLE oauth_accounts ADD COLUMN access_token TEXT;
ALTER TABLE oauth_accounts ADD COLUMN refresh_token TEXT;

-- เปลี่ยนชื่อ token_expires → token_expires_at
ALTER TABLE oauth_accounts CHANGE COLUMN token_expires token_expires_at DATETIME;

-- อัปเดตข้อมูล
UPDATE users SET has_password = TRUE, oauth_only = FALSE 
WHERE password_hash IS NOT NULL AND password_hash != '';

UPDATE users SET has_password = FALSE, oauth_only = TRUE 
WHERE password_hash IS NULL OR password_hash = '';

-- ตรวจสอบ
SELECT 'Migration completed!' as status;
DESCRIBE users;
DESCRIBE oauth_accounts;