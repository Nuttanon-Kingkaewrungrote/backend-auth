-- ============================================
-- Fund Dashboard - Complete Database Schema
-- Version: 2.0
-- Date: 2026-02-06
-- ============================================

-- ============================================
-- ตาราง users
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NULL COMMENT 'NULL สำหรับ OAuth-only users',
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    
    -- Email verification
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    
    -- Password reset
    reset_token VARCHAR(255),
    reset_token_expires DATETIME,
    
    -- Account type tracking
    has_password BOOLEAN DEFAULT TRUE COMMENT 'มี password หรือไม่ (OAuth-only = FALSE)',
    oauth_only BOOLEAN DEFAULT FALSE COMMENT 'สมัครผ่าน OAuth เท่านั้น',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    
    -- Indexes
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_verification_token (verification_token),
    INDEX idx_reset_token (reset_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ตาราง oauth_accounts
-- ============================================
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider VARCHAR(50) NOT NULL COMMENT 'google, facebook, github, etc.',
    provider_user_id VARCHAR(255) NOT NULL COMMENT 'User ID from OAuth provider',
    provider_email VARCHAR(255) COMMENT 'Email from OAuth provider',
    
    -- OAuth tokens
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at DATETIME,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Unique constraints
    UNIQUE KEY unique_provider_user (provider, provider_user_id),
    
    -- Indexes
    INDEX idx_user_provider (user_id, provider),
    INDEX idx_provider_email (provider_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- ข้อมูลเริ่มต้น (Optional)
-- ============================================

-- สร้าง admin user (password: admin123)
-- Hash: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF4rU/yy
INSERT INTO users (username, password_hash, email, role, email_verified, has_password, oauth_only)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF4rU/yy', 'admin@fundashboard.local', 'admin', TRUE, TRUE, FALSE)
ON DUPLICATE KEY UPDATE id=id;

-- ============================================
-- Stored Procedures (Optional - Utility Functions)
-- ============================================

DELIMITER //

-- ดูสถานะ user
CREATE PROCEDURE IF NOT EXISTS sp_get_user_info(IN p_user_id INT)
BEGIN
    SELECT 
        u.*,
        GROUP_CONCAT(oa.provider ORDER BY oa.created_at) as linked_providers
    FROM users u
    LEFT JOIN oauth_accounts oa ON u.id = oa.user_id
    WHERE u.id = p_user_id
    GROUP BY u.id;
END //

-- ดูรายการ OAuth accounts
CREATE PROCEDURE IF NOT EXISTS sp_get_user_oauth_accounts(IN p_user_id INT)
BEGIN
    SELECT 
        provider,
        provider_email,
        created_at,
        updated_at,
        CASE 
            WHEN token_expires_at > NOW() THEN 'Active'
            ELSE 'Expired'
        END as token_status
    FROM oauth_accounts
    WHERE user_id = p_user_id
    ORDER BY created_at DESC;
END //

DELIMITER ;

-- ============================================
-- Views (Optional - สำหรับ reporting)
-- ============================================

-- View: Users with OAuth info
CREATE OR REPLACE VIEW v_users_with_oauth AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.role,
    u.has_password,
    u.oauth_only,
    u.email_verified,
    u.created_at,
    u.last_login,
    GROUP_CONCAT(DISTINCT oa.provider ORDER BY oa.created_at) as oauth_providers,
    COUNT(DISTINCT oa.provider) as oauth_count
FROM users u
LEFT JOIN oauth_accounts oa ON u.id = oa.user_id
GROUP BY u.id, u.username, u.email, u.role, u.has_password, u.oauth_only, u.email_verified, u.created_at, u.last_login;

-- View: Active OAuth accounts
CREATE OR REPLACE VIEW v_active_oauth_accounts AS
SELECT 
    oa.*,
    u.username,
    u.email as user_email,
    CASE 
        WHEN oa.token_expires_at > NOW() THEN 'Active'
        WHEN oa.token_expires_at IS NULL THEN 'Unknown'
        ELSE 'Expired'
    END as token_status
FROM oauth_accounts oa
JOIN users u ON oa.user_id = u.id;

-- ============================================
-- Triggers (Optional - Auto-update logic)
-- ============================================

DELIMITER //

-- Auto-update has_password when password_hash changes
CREATE TRIGGER IF NOT EXISTS trg_users_update_has_password
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
    IF NEW.password_hash IS NOT NULL AND NEW.password_hash != '' THEN
        SET NEW.has_password = TRUE;
        SET NEW.oauth_only = FALSE;
    ELSE
        SET NEW.has_password = FALSE;
    END IF;
END //

DELIMITER ;

-- ============================================
-- Statistics & Validation Queries
-- ============================================

-- แสดงสถิติ users
SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN has_password = TRUE THEN 1 ELSE 0 END) as users_with_password,
    SUM(CASE WHEN oauth_only = TRUE THEN 1 ELSE 0 END) as oauth_only_users,
    SUM(CASE WHEN email_verified = TRUE THEN 1 ELSE 0 END) as verified_users
FROM users;

-- แสดงสถิติ OAuth
SELECT 
    provider,
    COUNT(*) as account_count,
    COUNT(DISTINCT user_id) as unique_users
FROM oauth_accounts
GROUP BY provider;

-- ============================================
-- Maintenance Queries
-- ============================================

-- ลบ verification tokens ที่หมดอายุ (เกิน 24 ชม.)
-- UPDATE users 
-- SET verification_token = NULL 
-- WHERE verification_token IS NOT NULL 
-- AND created_at < DATE_SUB(NOW(), INTERVAL 24 HOUR);

-- ลบ reset tokens ที่หมดอายุ
-- UPDATE users 
-- SET reset_token = NULL, reset_token_expires = NULL 
-- WHERE reset_token_expires < NOW();

-- ลบ OAuth tokens ที่หมดอายุนาน (เกิน 30 วัน)
-- UPDATE oauth_accounts 
-- SET access_token = NULL, refresh_token = NULL 
-- WHERE token_expires_at < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- ============================================
-- Backup & Export Commands
-- ============================================

/*
-- Backup database
mysqldump -u root -p fund_dashboard > backup_$(date +%Y%m%d_%H%M%S).sql

-- Export users only
mysqldump -u root -p fund_dashboard users > users_backup.sql

-- Export schema only
mysqldump -u root -p --no-data fund_dashboard > schema_only.sql

-- Restore
mysql -u root -p fund_dashboard < backup.sql
*/

-- ============================================
-- Schema Information
-- ============================================

SELECT 
    'Schema Version' as info, 
    '2.0' as value
UNION ALL
SELECT 
    'Total Tables', 
    COUNT(*) 
FROM information_schema.tables 
WHERE table_schema = 'fund_dashboard'
UNION ALL
SELECT 
    'Created Date', 
    '2026-02-06';

-- ============================================
-- End of Schema
-- ============================================

SELECT 'Schema created/updated successfully!' as status;