-- ============================================
-- Migration: Add UNIQUE constraint on email
-- รันใน MySQL ก่อน restart backend
-- ============================================

USE fund_dashboard;

-- 1. ลบ user ที่ email ซ้ำ (เก็บตัวแรก ลบที่เหลือ)
-- ดูก่อนว่ามี email ซ้ำไหม
SELECT email, COUNT(*) as cnt 
FROM users 
WHERE email IS NOT NULL AND email != '' 
GROUP BY email 
HAVING cnt > 1;

-- ถ้ามี email ซ้ำ ให้ลบ user ที่สร้างทีหลัง (เก็บ id ต่ำสุด)
-- ⚠️ ตรวจสอบให้ดีก่อนรัน!
DELETE u1 FROM users u1
INNER JOIN users u2
WHERE u1.email = u2.email
  AND u1.email IS NOT NULL
  AND u1.email != ''
  AND u1.id > u2.id;

-- 2. เพิ่ม UNIQUE constraint
ALTER TABLE users ADD UNIQUE INDEX idx_email_unique (email);

-- 3. ตรวจสอบ
DESCRIBE users;
SELECT 'Migration completed!' as status;