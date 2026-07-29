"""Töleg router"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi.util import get_remote_address
from slowapi import Limiter

from database import get_db
from models import Katilimci, Turnir
from schemas import SuccessResponse
from auth import get_current_user
from utils import send_telegram_message

router = APIRouter(tags=["Odeme"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/api/odeme-bilgi")
def api_odeme_bilgi(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    ref_code = current_user.get("sub")
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref_code).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady")

    turnir_tolek = "5 Manat"
    turnir_tolek_usuly = "TMCell SMS"
    if kat.turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == kat.turnir_id).first()
        if turnir:
            turnir_tolek = turnir.tolek
            turnir_tolek_usuly = turnir.tolek_usuly

    return {
        "success": True,
        "data": {
            "katilimci": {
                "referans_kodu": kat.referans_kodu,
                "ad": kat.ad,
                "odeme_durumu": kat.odeme_durumu
            },
            "turnir_tolek": turnir_tolek,
            "turnir_tolek_usuly": turnir_tolek_usuly
        }
    }


@router.post("/api/odeme-yapildi", response_model=SuccessResponse)
@limiter.limit("5/minute")
def api_odeme_yapildi(request: Request, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    ref = current_user.get("sub")
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    now = datetime.utcnow()
    kat.odeme_durumu = 1
    kat.odeme_tarihi = now
    db.commit()

    msg = f"💰 <b>TÖLEG!</b>\n\n👤 {kat.ad}\n🔑 {ref}\n📅 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(msg)
    logger.info(f"Odeme: {ref}")

    return {"success": True, "message": "Töleg bildirimi ugradyldy!"}
