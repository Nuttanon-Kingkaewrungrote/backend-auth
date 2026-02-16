-- ============================================
-- Rollback Script - ใช้เมื่อต้องการลบทุกอย่าง
-- ⚠️ ระวัง: จะลบข้อมูลทั้งหมด!
-- ============================================

USE fund_dashboard;

-- Drop triggers
DROP TRIGGER IF EXISTS trg_users_update_has_password;

-- Drop views
DROP VIEW IF EXISTS v_users_with_oauth;
DROP VIEW IF EXISTS v_active_oauth_accounts;

-- Drop procedures
DROP PROCEDURE IF EXISTS sp_get_user_info;
DROP PROCEDURE IF EXISTS sp_get_user_oauth_accounts;

-- Drop tables
DROP TABLE IF EXISTS oauth_accounts;
DROP TABLE IF EXISTS users;

-- Drop database (ถ้าต้องการลบทั้งหมด)
-- DROP DATABASE IF EXISTS fund_dashboard;

SELECT 'Rollback completed!' as status;