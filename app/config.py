import os
from typing import List, Optional
from pydantic import BaseSettings, validator
from functools import lru_cache
import secrets

class Settings(BaseSettings):
    # App
    APP_NAME: str = "FinHealth360 Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Plaid Configuration
    PLAID_CLIENT_ID: str
    PLAID_SECRET: str
    PLAID_ENVIRONMENT: str = "sandbox"
    
    # Encryption - Generate secure keys if not provided
    TOKEN_ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    DATA_ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./finhealth360.db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000"
    ]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    REDIS_URL: str = "redis://localhost:6379"
    
    # Webhook
    WEBHOOK_BASE_URL: str = "http://localhost:8000"
    
    # Health Data APIs (Future Integration)
    FITBIT_CLIENT_ID: Optional[str] = None
    FITBIT_CLIENT_SECRET: Optional[str] = None
    GOOGLE_FIT_CLIENT_ID: Optional[str] = None
    GOOGLE_FIT_CLIENT_SECRET: Optional[str] = None
    
    # Security Headers
    HSTS_MAX_AGE: int = 31536000  # 1 year
    CSP_DIRECTIVES: dict = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "img-src": ["'self'", "data:", "https:"]
    }
    
    @validator("PLAID_ENVIRONMENT")
    def validate_plaid_environment(cls, v):
        allowed_envs = ["sandbox", "development", "production"]
        if v not in allowed_envs:
            raise ValueError(f"PLAID_ENVIRONMENT must be one of {allowed_envs}")
        return v
    
    @validator("TOKEN_ENCRYPTION_KEY")
    def validate_encryption_key_length(cls, v):
        if len(v) < 32:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be at least 32 characters")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()