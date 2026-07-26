"""Authentication - JWT we parol hash"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Katilimci

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str) -> str:
    """Paroly hash et"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Paroly barla"""
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """JWT token döret"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict:
    """Token decode et"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Katilimci:
    """Häzirki ulanyjy (JWT arkaly)"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nadogry ýa-da wagty gutardy",
            headers={"WWW-Authenticate": "Bearer"},
        )

    referans_kodu = payload.get("sub")
    user = db.query(Katilimci).filter(Katilimci.referans_kodu == referans_kodu).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ulanyjy tapylmady",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Admin barlagy (JWT arkaly)"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin hukugy ýok",
        )

    return True

def verify_admin_password(sifre: str) -> bool:
    """Admin parolyny barla (düz tekst)"""
    return sifre == settings.admin_sifre_hash
