"""Sazlamalar - Pydantic Settings"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://user:pass@localhost/db"
    secret_key: str = "super-gizli-achar-32-symboldan-kop-bolmaly"
    admin_sifre_hash: str = "admin123"
    cloudflare_worker_url: str = ""
    frontend_url: str = "https://sizin-sayt.pages.dev"

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 gün

    class Config:
        env_file = ".env"
        extra = "ignore"  # Railway başga env variable-laryny ýykmasyn

settings = Settings()
