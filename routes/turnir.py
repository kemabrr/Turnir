"""Turnir router - public + gatnaşyk"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi.util import get_remote_address
from slowapi import Limiter

from database import get_db
from models import Katilimci, Turnir
from schemas import SuccessResponse, TurnirGosul
from auth import get_current_user
from utils import sanitize, validate_phone, get_stats, get_turnir_data, get_bayraklar, get_all_turnirler

router = APIRouter(tags=["Turnir"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/api/stats")
def api_stats(turnir_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"success": True, "stats": get_stats(db, turnir_id)}


@router.get("/api/turnir-data")
def api_turnir_data(turnir_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"success": True, "turnir": get_turnir_data(db, turnir_id)}


@router.get("/api/bayraklar")
def api_bayraklar(turnir_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"success": True, "bayraklar": get_bayraklar(db, turnir_id)}


@router.get("/api/turnirler")
def api_turnirler(status: Optional[str] = None, mode: Optional[str] = None, db: Session = Depends(get_db)):
    return {"success": True, "turnirler": get_all_turnirler(db, status, mode)}


@router.post("/api/turnir-gosul", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_turnir_gosul(request: Request, data: TurnirGosul, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    pubg_id = sanitize(data.pubg_id, 20)
    payment_phone = str(data.payment_phone or "").strip()
    tournament_id = sanitize(data.tournament_id or "", 50)
    turnir_id = data.turnir_id

    if not pubg_id or len(pubg_id) < 8 or not pubg_id.isdigit():
        raise HTTPException(status_code=400, detail="PUBG ID diňe san bolmaly (minimum 8)!")

    ref = current_user.get("sub")

    if not turnir_id:
        turnir_id = 1

    turnir = db.query(Turnir).filter(Turnir.id == turnir_id).first()
    if not turnir:
        raise HTTPException(status_code=404, detail="Turnir tapylmady!")

    is_tolekli = turnir.tolekli == 1

    if is_tolekli:
        valid, phone_clean = validate_phone(payment_phone)
        if not valid:
            raise HTTPException(status_code=400, detail="Telefon belgisi nadogry!")
    else:
        phone_clean = payment_phone if payment_phone else ""

    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()

    if not is_tolekli:
        now = datetime.utcnow()
        kat.pubg_id = pubg_id
        kat.payment_phone = phone_clean
        kat.tournament_id = tournament_id
        kat.turnir_id = turnir_id
        kat.odeme_durumu = 1
        kat.admin_onay = 1
        kat.onay_tarihi = now
        db.commit()
        logger.info(f"Turnir goşul (tolegsiz): {ref} -> turnir_id: {turnir_id}")
        return {
            "success": True,
            "message": "Turnira üstünlikli goşuldyňyz!",
            "data": {"turnir_id": turnir_id, "auto_approved": True}
        }

    kat.pubg_id = pubg_id
    kat.payment_phone = phone_clean
    kat.tournament_id = tournament_id
    kat.turnir_id = turnir_id
    db.commit()

    logger.info(f"Turnir goşul (tolekli): {ref} -> turnir_id: {turnir_id}")
    return {
        "success": True,
        "message": "Turnira goşuldyňyz! Indi töleg ediň.",
        "data": {"turnir_id": turnir_id}
    }
