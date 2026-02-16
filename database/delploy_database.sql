-- ============================================
-- Fund Dashboard - Complete Database Deployment
-- Version: 2.1 - Production Ready
-- Date: 2026-02-16
-- ============================================

-- ============================================
-- 1. CREATE DATABASE
-- ============================================
CREATE DATABASE IF NOT EXISTS fund_dashboard 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE fund_dashboard;

-- ============================================
-- 2. CREATE TABLE: users
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    -- Primary Key
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Authentication
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NULL COMMENT 'NULL สำหรับ OAuth-only users',
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    
    -- Profile
    display_name VARCHAR(100) NULL,
    avatar_url VARCHAR(500) NULL,
    
    -- Email Verification
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    
    -- Password Reset
    reset_token VARCHAR(255),
    reset_token_expires DATETIME,
    
    -- Account Type Tracking
    has_password BOOLEAN DEFAULT TRUE COMMENT 'มี password หรือไม่',
    oauth_only BOOLEAN DEFAULT FALSE COMMENT 'สมัครผ่าน OAuth เท่านั้น',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    
    -- Indexes
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_verification_token (verification_token),
    INDEX idx_reset_token (reset_token),
    UNIQUE INDEX idx_email_unique (email)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. CREATE TABLE: oauth_accounts
-- ============================================
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- OAuth Provider Info
    provider VARCHAR(50) NOT NULL COMMENT 'google, facebook, github',
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    
    -- OAuth Tokens
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at DATETIME,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys & Constraints
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_provider_user (provider, provider_user_id),
    INDEX idx_user_provider (user_id, provider),
    INDEX idx_provider_email (provider_email)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. UPDATE EXISTING DATA (Migration)
-- ============================================
UPDATE users 
SET has_password = TRUE, oauth_only = FALSE 
WHERE password_hash IS NOT NULL AND password_hash != '';

UPDATE users 
SET has_password = FALSE, oauth_only = TRUE 
WHERE password_hash IS NULL OR password_hash = '';

-- ============================================
-- 5. STORED PROCEDURES
-- ============================================
DELIMITER //

DROP PROCEDURE IF EXISTS sp_get_user_info//
CREATE PROCEDURE sp_get_user_info(IN p_user_id INT)
BEGIN
    SELECT 
        u.*,
        GROUP_CONCAT(oa.provider ORDER BY oa.created_at) as linked_providers
    FROM users u
    LEFT JOIN oauth_accounts oa ON u.id = oa.user_id
    WHERE u.id = p_user_id
    GROUP BY u.id;
END //

DROP PROCEDURE IF EXISTS sp_get_user_oauth_accounts//
CREATE PROCEDURE sp_get_user_oauth_accounts(IN p_user_id INT)
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
-- 6. VIEWS
-- ============================================
CREATE OR REPLACE VIEW v_users_with_oauth AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.display_name,
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
GROUP BY u.id, u.username, u.email, u.display_name, u.role, 
         u.has_password, u.oauth_only, u.email_verified, 
         u.created_at, u.last_login;

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
-- 7. TRIGGERS
-- ============================================
DELIMITER //

DROP TRIGGER IF EXISTS trg_users_update_has_password//
CREATE TRIGGER trg_users_update_has_password
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
-- 8. DEFAULT DATA
-- ============================================
-- Admin user (password: admin123)
INSERT INTO users (
    username, password_hash, email, role, 
    email_verified, has_password, oauth_only, display_name
)
VALUES (
    'admin', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF4rU/yy', 
    'admin@fundashboard.local', 
    'admin', 
    TRUE, TRUE, FALSE,
    'System Administrator'
)
ON DUPLICATE KEY UPDATE id=id;

-- ============================================
-- 9. VALIDATION
-- ============================================
SELECT 'Deployment Complete!' as status;

SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN has_password = TRUE THEN 1 ELSE 0 END) as users_with_password,
    SUM(CASE WHEN oauth_only = TRUE THEN 1 ELSE 0 END) as oauth_only_users,
    SUM(CASE WHEN email_verified = TRUE THEN 1 ELSE 0 END) as verified_users
FROM users;