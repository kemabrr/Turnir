"""Sazlamalar - Pydantic Settings"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://user:pass@localhost/db"
    secret_key: str = "super-gizli-achar-32-symboldan-kop-bolmaly"
    admin_sifre_hash: str = "admin123"
    cloudflare_worker_url: str = ""          # ← Muny goýber (başga ýerde ulanýan bolsaň)
    frontend_url: str = "https://sizin-sayt.pages.dev"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    
    # TÄZE — şulary goş
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
