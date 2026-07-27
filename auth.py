"""Auth utilities - bcrypt bilen"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
import bcrypt

# JWT sazlamalary
SECRET_KEY = os.getenv("SECRET_KEY", "sizin-gizli-acharynyz-buraya-yazin")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 hepde


def hash_password(password: str) -> str:
    """Paroly hash et - bcrypt 72 byte çäkli"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 71:
        password_bytes = password_bytes[:71]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Paroly barla"""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 71:
        password_bytes = password_bytes[:71]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT token döret"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    """JWT token decode et"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_admin_password(password: str) -> bool:
    """Admin parolyny barla"""
    from config import settings
    hash_val = settings.admin_sifre_hash

    # Eger hash boş ýa-da default "admin123" bolsa - düz metin barla
    if not hash_val or hash_val == "admin123":
        return password == "admin123"

    # Hash edilen paroly barla
    return verify_password(password, hash_val)


# FastAPI dependency
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Häzirki ulanyjy barla - JWT payload dict döndürýär"""
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nadogry token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Admin barla"""
    payload = get_current_user(credentials)
    if not payload.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin hukuklary ýok",
        )
    return payload
