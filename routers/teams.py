"""Topar router"""
import re
import random
import string
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi.util import get_remote_address
from slowapi import Limiter

from database import get_db
from models import Katilimci, Takim
from schemas import SuccessResponse, TakimOlustur, TakimaKatil
from auth import get_current_user
from utils import sanitize, send_telegram_message

router = APIRouter(tags=["Takim"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/api/takim-bilgi")
def api_takim_bilgi(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    ref_code = current_user.get("sub")
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref_code).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady")
    return {"success": True, "data": {"katilimci": {"referans_kodu": kat.referans_kodu, "ad": kat.ad, "takim_kodu": kat.takim_kodu}}}


@router.post("/api/takim-olustur", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_takim_olustur(request: Request, data: TakimOlustur, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lider_ref = current_user.get("sub")
    takim_adi = sanitize(data.takim_adi, 50)

    if len(takim_adi) < 2 or len(takim_adi) > 50:
        raise HTTPException(status_code=400, detail="Topar ady 2-50 harp aralygynda bolmaly!")

    lider = db.query(Katilimci).filter(Katilimci.referans_kodu == lider_ref).first()
    if not lider:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")
    if lider.takim_kodu:
        raise HTTPException(status_code=400, detail="Siz eýýäm topar bolduňyz!")

    kod = "TEAM-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))

    new_takim = Takim(takim_kodu=kod, takim_adi=takim_adi, lider_referans=lider_ref)
    db.add(new_takim)

    lider.takim_kodu = kod
    lider.takim_lideri = 1
    db.commit()

    # TÄZE — şuny goş (db.commit()-den soň, return-dan öň)
    msg = f"🏰 <b>TÄZE TOPAR DÖREDILDI!</b>\n\n👤 Lider: {lider.ad}\n🔑 {lider_ref}\n👥 Topar: {takim_adi}\n🎫 Kod: {kod}"
    send_telegram_message(msg)

    logger.info(f"Topar: {kod} - {takim_adi}")
    return {"success": True, "message": "Topar üstünlikli döredildi!", "data": {"takim_kodu": kod}}
"data": {"takim_kodu": kod}}


@router.post("/api/takima-katil", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_takima_katil(request: Request, data: TakimaKatil, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    uye_ref = current_user.get("sub")
    takim_kodu = str(data.takim_kodu).strip().upper()

    if not re.match(r"^TEAM-[A-Z0-9]{5}$", takim_kodu):
        raise HTTPException(status_code=400, detail="Topar kody nädogry format!")

    uye = db.query(Katilimci).filter(Katilimci.referans_kodu == uye_ref).first()
    if not uye:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")
    if uye.takim_kodu:
        raise HTTPException(status_code=400, detail="Siz eýýäm topar bolduňyz!")

    takim = db.query(Takim).filter(Takim.takim_kodu == takim_kodu).first()
    if not takim:
        raise HTTPException(status_code=404, detail="Topar kody nädogry!")

    say = db.query(Katilimci).filter(Katilimci.takim_kodu == takim_kodu).count()
    if say >= 4:
        raise HTTPException(status_code=400, detail="Bu topar doly (4 kişi)!")

    uye.takim_kodu = takim_kodu

    if not takim.uye1_referans:
        takim.uye1_referans = uye_ref
    elif not takim.uye2_referans:
        takim.uye2_referans = uye_ref
    elif not takim.uye3_referans:
        takim.uye3_referans = uye_ref

    db.commit()

    msg = f"👥 <b>TOPARA TÄZE AGZA!</b>\n\nTopar: {takim.takim_adi or 'Topar'}\nKod: {takim_kodu}\n👤 {uye.ad}"
    send_telegram_message(msg)
    logger.info(f"Katil: {takim_kodu} - {uye.ad}")

    return {"success": True, "message": f"Topara goşuldyňyz! ({say+1}/4)"}
