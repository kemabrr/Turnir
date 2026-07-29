# migrate.py
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")  # Railway-da awtomatik bar
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"sslmode": "require"})

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE turnirler ADD COLUMN lobi_kodu VARCHAR(50);"))
    conn.commit()
    print("✅ lobi_kodu goşuldy!")
