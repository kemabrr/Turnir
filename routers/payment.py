"""Töleg router"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from slowapi.util import get_remote_address
from slowapi import Limiter

from database import get_db
from models import Katilimci, Turnir
from schemas import SuccessResponse
from auth import get_current_user
from utils import send_telegram_message, send_telegram_photo

router = APIRouter(tags=["Odeme"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SKRINSHOT_SIZE = 5 * 1024 * 1024  # 5 MB


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


@router.post("/api/odeme-skrinshot-yukle", response_model=SuccessResponse)
@limiter.limit("5/minute")
async def api_odeme_skrinshot_yukle(
    request: Request,
    skrinshot: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ulanyjy: Töleg SMS skrinshotyny ýükle - göni Telegram bot-a ugradylýar"""
    ref = current_user.get("sub")
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    if skrinshot.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Diňe surat faýly (JPG, PNG, WEBP) ýüklemek bolýar!")

    content = await skrinshot.read()

    if not content:
        raise HTTPException(status_code=400, detail="Surat boş!")

    if len(content) > MAX_SKRINSHOT_SIZE:
        raise HTTPException(status_code=400, detail="Surat 5MB-dan uly bolmaly däl!")

    now = datetime.utcnow()
    kat.odeme_durumu = 1
    kat.odeme_tarihi = now
    db.commit()

    turnir_ady = "-"
    if kat.turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == kat.turnir_id).first()
        if turnir:
            turnir_ady = turnir.ad

    caption = (
        "💰 <b>TÖLEG SKRINSHOTY!</b>\n\n"
        f"👤 {kat.ad}\n"
        f"🔑 {ref}\n"
        f"📞 {kat.telefon}\n"
        f"🏆 {turnir_ady}\n"
        f"📅 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    sent = send_telegram_photo(content, skrinshot.filename or f"{ref}.jpg", caption)
    if not sent:
        logger.warning(f"Telegram surat ugradylmady: {ref}")

    logger.info(f"Odeme skrinshot ugradyldy: {ref}")
    return {
        "success": True,
        "message": "Töleg skrinshotyňyz ugradyldy! Admin tassyklamasyna garaşyň."
    }
