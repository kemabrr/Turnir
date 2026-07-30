"""Sazlamalar - Pydantic Settings"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://user:pass@localhost/db"
    secret_key: str = "super-gizli-achar-32-symboldan-kop-bolmaly"
    admin_sifre_hash: str = "admin123"
    cloudflare_worker_url: str = ""
    frontend_url: str = "https://sizin-sayt.pages.dev"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # TÄZE — Kanal URL-leri (Railway Environment Variables bilen goýup bilersiňiz)
    telegram_kanal_url: str = "https://t.me/sizin_kanal"
    imo_kanal_url: str = "https://imo.im/sizin_kanal"
    link_kanal_url: str = "https://groups.linkm.me/#CjQKIKkEZDPW8IgZRwTIfOLwn811dKgSuRWcVK4vtDK2UWFAEhBM9gLE1A4csbHzjRSyfO09"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
