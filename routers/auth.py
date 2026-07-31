"""Auth router - kayit, login, logout"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi.util import get_remote_address
from slowapi import Limiter

from database import get_db
from models import Katilimci
from schemas import UserCreate, UserLogin, SuccessResponse
from auth import hash_password, verify_password, create_access_token
from utils import generate_ref_code, validate_phone, sanitize, send_telegram_message

router = APIRouter(tags=["Auth"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/api/kayit-ol", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_kayit_ol(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    ad = sanitize(data.ad, 100)
    telefon = str(data.telefon).strip()
    parol = data.parol
    parol_tekrar = data.parol_tekrar

    if not all([ad, telefon, parol]):
        raise HTTPException(status_code=400, detail="Ahli maglumatlary dolduryň!")

    if len(parol) < 6:
        raise HTTPException(status_code=400, detail="Parol 6 harpdan uly bolmaly!")

    if parol != parol_tekrar:
        raise HTTPException(status_code=400, detail="Parollar deň däl!")

    valid, telefon_clean = validate_phone(telefon)
    if not valid:
        raise HTTPException(status_code=400, detail="Telefon belgisi nadogry! Format: +993 XX XXX XXX ýa-da 8 san")

    if len(ad) < 2:
        raise HTTPException(status_code=400, detail="Ad 2 harpdan uly bolmaly!")

    existing = db.query(Katilimci).filter(Katilimci.telefon == telefon_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu telefon belgisi bilen eýýäm hasap açylypdyr!")

    ref = generate_ref_code(db)
    parol_hash = hash_password(parol)
    now = datetime.utcnow()

    new_user = Katilimci(
        referans_kodu=ref,
        ad=ad,
        telefon=telefon_clean,
        parol_hash=parol_hash,
        kayit_tarihi=now
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    msg = f"🎮 <b>TÄZE KATYLYJY!</b>\n\n👤 {ad}\n📞 {telefon_clean}\n🔑 {ref}"
    send_telegram_message(msg)
    logger.info(f"Kayit: {ref} - {ad}")

    token = create_access_token({"sub": ref, "type": "user"})

    return {
        "success": True,
        "message": "Ustunlikli!",
        "data": {"referans_kodu": ref, "access_token": token}
    }


@router.post("/api/login", response_model=SuccessResponse)
@limiter.limit("5/minute")
def api_login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    telefon = str(data.telefon).strip()
    parol = data.parol

    if not all([telefon, parol]):
        raise HTTPException(status_code=400, detail="Telefon we parol girizin!")

    valid, telefon_clean = validate_phone(telefon)
    if not valid:
        raise HTTPException(status_code=400, detail="Telefon belgisi nadogry!")

    kat = db.query(Katilimci).filter(Katilimci.telefon == telefon_clean).first()

    if not kat or not verify_password(parol, kat.parol_hash):
        raise HTTPException(status_code=400, detail="Telefon belgisi ýa-da parol nädogry!")

    token = create_access_token({"sub": kat.referans_kodu, "type": "user"})
    logger.info(f"Login: {kat.referans_kodu} - {kat.ad}")

    return {
        "success": True,
        "message": "Giriş üstünlikli!",
        "data": {"referans_kodu": kat.referans_kodu, "access_token": token}
    }


@router.post("/api/logout")
def api_logout():
    return {"success": True, "message": "Çykyş üstünlikli!"}
