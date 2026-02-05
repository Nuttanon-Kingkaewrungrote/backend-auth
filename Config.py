"""
Configuration Management & Validation
ใช้สำหรับตรวจสอบ environment variables และ config
"""

import os
from dotenv import load_dotenv
from typing import Optional
import secrets

load_dotenv()


class Config:
    """Application Configuration with Validation"""
    
    # ============================================
    # Required Configuration
    # ============================================
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    
    # Database
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_USER: str = os.getenv('DB_USER', 'root')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', '')
    DB_NAME: str = os.getenv('DB_NAME', 'fund_dashboard')
    
    # ============================================
    # Optional Configuration (OAuth)
    # ============================================
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv('GOOGLE_REDIRECT_URI')
    
    # ============================================
    # Optional Configuration (Email)
    # ============================================
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_USER: Optional[str] = os.getenv('EMAIL_USER')
    EMAIL_PASSWORD: Optional[str] = os.getenv('EMAIL_PASSWORD')
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:8000')
    
    # ============================================
    # Application Settings
    # ============================================
    ALGORITHM: str = 'HS256'
    
    # Environment
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    
    @classmethod
    def validate_required(cls) -> list[str]:
        """ตรวจสอบ required configuration"""
        errors = []
        
        # 1. ตรวจสอบ SECRET_KEY
        if not cls.SECRET_KEY:
            errors.append("❌ SECRET_KEY is not set in .env file")
        elif cls.SECRET_KEY == 'your-secret-key-change-this':
            errors.append("⚠️  SECRET_KEY is still using default value! Please change it for security.")
        elif len(cls.SECRET_KEY) < 32:
            errors.append("⚠️  SECRET_KEY should be at least 32 characters long")
        
        # 2. ตรวจสอบ Database
        if not cls.DB_HOST:
            errors.append("❌ DB_HOST is not set")
        if not cls.DB_USER:
            errors.append("❌ DB_USER is not set")
        if not cls.DB_NAME:
            errors.append("❌ DB_NAME is not set")
        
        # 3. ตรวจสอบ Database Password (production only)
        if cls.ENVIRONMENT == 'production' and not cls.DB_PASSWORD:
            errors.append("❌ DB_PASSWORD must be set in production!")
        
        return errors
    
    @classmethod
    def validate_optional(cls) -> list[str]:
        """ตรวจสอบ optional features และแจ้งเตือน"""
        warnings = []
        
        # Google OAuth
        if not cls.GOOGLE_CLIENT_ID or not cls.GOOGLE_CLIENT_SECRET:
            warnings.append("⚠️  Google OAuth is not configured (GOOGLE_CLIENT_ID/SECRET missing)")
            warnings.append("   → Google login will not work")
        
        # Email Service
        if not cls.EMAIL_USER or not cls.EMAIL_PASSWORD:
            warnings.append("⚠️  Email service is not configured (EMAIL_USER/PASSWORD missing)")
            warnings.append("   → Email verification and password reset will not work")
        
        return warnings
    
    @classmethod
    def validate_all(cls, strict: bool = False) -> bool:
        """
        ตรวจสอบ configuration ทั้งหมด
        
        Args:
            strict: ถ้าเป็น True จะ raise exception เมื่อพบ error
        
        Returns:
            True ถ้าผ่านการตรวจสอบ
        """
        print("=" * 60)
        print("🔍 Validating Configuration...")
        print("=" * 60)
        
        # ตรวจสอบ required
        errors = cls.validate_required()
        
        if errors:
            print("\n❌ Configuration Errors:")
            for error in errors:
                print(f"   {error}")
        
        # ตรวจสอบ optional
        warnings = cls.validate_optional()
        
        if warnings:
            print("\n⚠️  Configuration Warnings:")
            for warning in warnings:
                print(f"   {warning}")
        
        # สรุปผล
        if not errors:
            print("\n✅ All required configuration is valid!")
        
        print("=" * 60)
        
        # ถ้า strict mode และมี error ให้ raise exception
        if strict and errors:
            raise ValueError(
                "Configuration validation failed! Please check your .env file.\n" +
                "\n".join(errors)
            )
        
        return len(errors) == 0
    
    @classmethod
    def print_config_summary(cls):
        """แสดงสรุป configuration (ซ่อนค่าลับ)"""
        print("\n📋 Configuration Summary:")
        print(f"   Environment: {cls.ENVIRONMENT}")
        print(f"   Debug Mode: {cls.DEBUG}")
        print(f"   Database: {cls.DB_USER}@{cls.DB_HOST}/{cls.DB_NAME}")
        print(f"   Frontend URL: {cls.FRONTEND_URL}")
        print(f"   Google OAuth: {'✅ Enabled' if cls.GOOGLE_CLIENT_ID else '❌ Disabled'}")
        print(f"   Email Service: {'✅ Enabled' if cls.EMAIL_USER else '❌ Disabled'}")
        print()
    
    @classmethod
    def generate_secret_key(cls) -> str:
        """สร้าง SECRET_KEY แบบสุ่ม"""
        return secrets.token_urlsafe(32)


# ============================================
# Security Utilities
# ============================================

class SecurityConfig:
    """Security-related configurations"""
    
    # CORS Settings
    @staticmethod
    def get_cors_origins() -> list[str]:
        """ดึง allowed origins สำหรับ CORS"""
        env = Config.ENVIRONMENT
        
        if env == 'production':
            # Production: เฉพาะ domain ที่กำหนด
            return [
                "https://yourdomain.com",
                "https://www.yourdomain.com",
            ]
        elif env == 'staging':
            # Staging
            return [
                "https://staging.yourdomain.com",
            ]
        else:
            # Development: allow localhost
            return [
                "http://localhost:3000",      # React
                "http://localhost:5173",      # Vite
                "http://localhost:8000",      # FastAPI docs
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8000",
            ]
    
    @staticmethod
    def get_trusted_hosts() -> list[str]:
        """ดึง trusted hosts"""
        env = Config.ENVIRONMENT
        
        if env == 'production':
            return ["yourdomain.com", "www.yourdomain.com"]
        else:
            return ["localhost", "127.0.0.1"]
    
    # Rate Limiting
    RATE_LIMIT_LOGIN = "5/minute"
    RATE_LIMIT_REGISTER = "3/minute"
    RATE_LIMIT_PASSWORD_RESET = "3/hour"
    
    # JWT Settings
    ACCESS_TOKEN_EXPIRE_HOURS = 24
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    RESET_TOKEN_EXPIRE_HOURS = 1
    
    # Password Requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = False


# ============================================
# Helper Functions
# ============================================

def check_database_connection() -> bool:
    """ตรวจสอบการเชื่อมต่อฐานข้อมูล"""
    try:
        import pymysql
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def check_email_service() -> bool:
    """ตรวจสอบ email service"""
    if not Config.EMAIL_USER or not Config.EMAIL_PASSWORD:
        return False
    
    try:
        import smtplib
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
        return True
    except Exception as e:
        print(f"❌ Email service connection failed: {e}")
        return False


def startup_checks():
    """ตรวจสอบทุกอย่างก่อน start application"""
    print("\n" + "=" * 60)
    print("🚀 Starting Up...")
    print("=" * 60)
    
    # 1. Validate configuration
    config_valid = Config.validate_all(strict=False)
    
    # 2. Print config summary
    Config.print_config_summary()
    
    # 3. Check database
    print("🔍 Checking Database Connection...")
    db_ok = check_database_connection()
    if db_ok:
        print("   ✅ Database connection OK")
    else:
        print("   ❌ Database connection FAILED")
    
    # 4. Check email service (optional)
    if Config.EMAIL_USER and Config.EMAIL_PASSWORD:
        print("🔍 Checking Email Service...")
        email_ok = check_email_service()
        if email_ok:
            print("   ✅ Email service OK")
        else:
            print("   ⚠️  Email service connection failed (emails will not be sent)")
    
    print("=" * 60)
    
    # ถ้า required services ไม่ ok ให้แจ้งเตือน
    if not config_valid or not db_ok:
        print("\n⚠️  Warning: Some required services are not properly configured!")
        print("   Please check your .env file and database connection.")
        print()
    
    return config_valid and db_ok


# ============================================
# CLI Commands
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "validate":
            # python config.py validate
            Config.validate_all(strict=True)
            print("\n✅ Configuration is valid!")
        
        elif command == "generate-secret":
            # python config.py generate-secret
            secret = Config.generate_secret_key()
            print(f"\n🔑 Generated SECRET_KEY:")
            print(f"   {secret}")
            print(f"\n   Add this to your .env file:")
            print(f"   SECRET_KEY={secret}")
        
        elif command == "check":
            # python config.py check
            startup_checks()
        
        else:
            print("Unknown command. Available commands:")
            print("  validate       - Validate configuration")
            print("  generate-secret - Generate new SECRET_KEY")
            print("  check          - Run all startup checks")
    
    else:
        # แสดงสรุป config
        Config.validate_all()
        Config.print_config_summary()