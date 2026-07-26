"""Sazlamalar"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Railway awtomatik berýär
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    secret_key: str = os.getenv("SECRET_KEY", "super-gizli-achar-32-symboldan-kop-bolmaly")
    admin_sifre_hash: str = os.getenv("ADMIN_SIFRE_HASH", "admin123")
    cloudflare_worker_url: str = os.getenv("CLOUDFLARE_WORKER_URL", "")

    # JWT
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 gün

    # CORS - Cloudflare Pages URL-iňiz
    frontend_url: str = os.getenv("FRONTEND_URL", "https://sizin-sayt.pages.dev")

    class Config:
        env_file = ".env"

settings = Settings()
