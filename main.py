"""FastAPI Backend - PUBG Turnir"""
import os
import random
import string
import re
import logging
import hashlib
import requests
from datetime import datetime, timedelta
from html import escape as html_escape
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from database import engine, Base, get_db
from models import Katilimci, Takim, Turnir, Ayar
from schemas import *
from auth import (
    hash_password, verify_password, create_access_token, decode_token,
    get_current_user, get_current_admin, verify_admin_password
)

# Tablisalary döret
Base.metadata.create_all(bind=engine)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="PUBG Turnir API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG") else None,
    redoc_url=None
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Cloudflare Pages üçin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://turnirhtml.pages.dev",  # Siziň frontend URL-iňiz
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


security = HTTPBearer()

# ===================== HELPERS =====================

def get_ayar(key: str, default: str = "", db: Session = None) -> str:
    if db is None:
        return default
    row = db.query(Ayar).filter(Ayar.key == key).first()
    return row.value if row else default

def set_ayar_db(key: str, value: str, db: Session):
    ayar = db.query(Ayar).filter(Ayar.key == key).first()
    if ayar:
        ayar.value = value
    else:
        ayar = Ayar(key=key, value=value)
        db.add(ayar)
    db.commit()

def generate_ref_code(db: Session) -> str:
    while True:
        code = "PUBG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not db.query(Katilimci).filter(Katilimci.referans_kodu == code).first():
            return code

def send_telegram_message(message: str) -> bool:
    if not settings.cloudflare_worker_url:
        logger.warning("CLOUDFLARE_WORKER_URL bosh!")
        return False
    url = f"{settings.cloudflare_worker_url}/send-message"
    try:
        response = requests.post(url, json={"message": message}, timeout=15)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Telegram error: {e}")
        return False

def get_stats(db: Session, turnir_id: int = None) -> dict:
    query = db.query(Katilimci)
    if turnir_id:
        query = query.filter(Katilimci.turnir_id == turnir_id)

    toplam = query.count()
    odeme_yapan = query.filter(Katilimci.odeme_durumu == 1).count()
    onaylanan = query.filter(Katilimci.admin_onay == 1).count()

    if turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == turnir_id).first()
        yer_sany = turnir.yer_sany if turnir else 100
    else:
        yer_sany = int(get_ayar("turnir_yer_sany", "100", db))

    return {
        "toplam": toplam,
        "odeme_yapan": odeme_yapan,
        "onaylanan": onaylanan,
        "yer_sany": yer_sany,
        "galan": max(0, yer_sany - onaylanan)
    }

def get_turnir_data(db: Session, turnir_id: int = None) -> dict:
    if turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == turnir_id).first()
        if turnir:
            return {
                "id": turnir.id,
                "ad": turnir.ad,
                "senesi": turnir.senesi,
                "wagty": turnir.wagty,
                "karta": turnir.karta,
                "gatnasym": turnir.gatnasym,
                "tolek": turnir.tolek,
                "tolek_usuly": turnir.tolek_usuly,
                "mode": turnir.mode,
                "tolekli": turnir.tolekli
            }
    return {
        "id": None,
        "ad": "PUBG MOBILE SQUAD",
        "senesi": get_ayar("turnir_senesi", "", db),
        "wagty": get_ayar("turnir_wagty", "", db),
        "karta": get_ayar("turnir_karta", "", db),
        "gatnasym": get_ayar("turnir_gatnasym", "", db),
        "tolek": get_ayar("turnir_tolek", "", db),
        "tolek_usuly": get_ayar("turnir_tolek_usuly", "", db),
        "mode": "squad",
        "tolekli": 1
    }

def get_bayraklar(db: Session, turnir_id: int = None) -> dict:
    if turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == turnir_id).first()
        if turnir:
            b1 = turnir.bayrak_1.split("|")
            b2 = turnir.bayrak_2.split("|")
            b3 = turnir.bayrak_3.split("|")
            return {
                "bir": {"mukdar": b1[0], "bonus": b1[1] if len(b1) > 1 else ""},
                "iki": {"mukdar": b2[0], "bonus": b2[1] if len(b2) > 1 else ""},
                "uc": {"mukdar": b3[0], "bonus": b3[1] if len(b3) > 1 else ""},
                "jemi": turnir.bayrak_jemi
            }
    b1 = get_ayar("bayrak_1", "300 Manat|+ 🏆 Kubok", db).split("|")
    b2 = get_ayar("bayrak_2", "150 Manat", db).split("|")
    b3 = get_ayar("bayrak_3", "50 Manat", db).split("|")
    return {
        "bir": {"mukdar": b1[0], "bonus": b1[1] if len(b1) > 1 else ""},
        "iki": {"mukdar": b2[0], "bonus": b2[1] if len(b2) > 1 else ""},
        "uc": {"mukdar": b3[0], "bonus": b3[1] if len(b3) > 1 else ""},
        "jemi": get_ayar("bayrak_jemi", "500 M", db)
    }

def get_all_turnirler(db: Session, status: str = None, mode: str = None) -> List[dict]:
    query = db.query(Turnir)
    if status:
        query = query.filter(Turnir.status == status)
    if mode:
        query = query.filter(Turnir.mode == mode)
    rows = query.order_by(Turnir.created_at.desc()).all()

    result = []
    for row in rows:
        stats = get_stats(db, row.id)
        result.append({
            "id": row.id,
            "ad": row.ad,
            "senesi": row.senesi,
            "wagty": row.wagty,
            "karta": row.karta,
            "mode": row.mode,
            "gatnasym": row.gatnasym,
            "tolek": row.tolek,
            "tolek_usuly": row.tolek_usuly,
            "yer_sany": row.yer_sany,
            "bayrak_jemi": row.bayrak_jemi,
            "status": row.status,
            "tolekli": row.tolekli,
            "onaylanan": stats["onaylanan"],
            "galan": stats["galan"]
        })
    return result

def validate_phone(phone: str):
    if not phone:
        return False, None
    cleaned = re.sub(r"[\s\-\+\(\)]", "", phone)
    if not cleaned.isdigit():
        return False, None
    if len(cleaned) == 8:
        return True, cleaned
    if len(cleaned) == 11 and cleaned.startswith("993"):
        return True, cleaned[3:]
    return False, None

def sanitize(text, max_len=100):
    if not text:
        return ""
    return html_escape(str(text).strip())[:max_len]

# ===================== ROUTES =====================

@app.get("/")
def home(db: Session = Depends(get_db)):
    return {
        "message": "Backend işleýär!",
        "status": "ok",
        "version": "1.0.0"
    }

@app.get("/api/stats")
def api_stats(turnir_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"success": True, "stats": get_stats(db, turnir_id)}

@app.get("/api/turnir-data")
def api_turnir_data(turnir_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"success": True, "turnir": get_turnir_data(db, turnir_id)}

@app.get("/api/bayraklar")
def api_bayraklar(turnir_id: Optional[int] = None, db: Session = Depends(get_db)):
    return {"success": True, "bayraklar": get_bayraklar(db, turnir_id)}

@app.get("/api/turnirler")
def api_turnirler(status: Optional[str] = None, mode: Optional[str] = None, db: Session = Depends(get_db)):
    return {"success": True, "turnirler": get_all_turnirler(db, status, mode)}

# ---------- AUTH ----------

@app.post("/api/kayit-ol", response_model=SuccessResponse)
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

@app.post("/api/login", response_model=SuccessResponse)
@limiter.limit("5/minute")
def api_login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    telefon = str(data.telefon).strip()
    parol = data.parol

    if not all([telefon, parol]):
        raise HTTPException(status_code=400, detail="Telefon we parol girizin!")

    valid, telefon_clean = validate_phone(telefon)
    if not valid:
        raise HTTPException(status_code=400, detail="Telefon belgisi nadogry!")

    kat = db.query(Katilimci).filter(
        Katilimci.telefon == telefon_clean
    ).first()

    if not kat or not verify_password(parol, kat.parol_hash):
        raise HTTPException(status_code=400, detail="Telefon belgisi ýa-da parol nädogry!")

    token = create_access_token({"sub": kat.referans_kodu, "type": "user"})
    logger.info(f"Login: {kat.referans_kodu} - {kat.ad}")

    return {
        "success": True,
        "message": "Giriş üstünlikli!",
        "data": {"referans_kodu": kat.referans_kodu, "access_token": token}
    }

@app.post("/api/logout")
def api_logout():
    return {"success": True, "message": "Çykyş üstünlikli!"}

# ---------- PROFIL ----------

@app.get("/api/profil", response_model=SuccessResponse)
def api_profil(current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    ref_code = current_user.referans_kodu

    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref_code).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady")

    takim = db.query(Takim).filter(Takim.takim_kodu == kat.takim_kodu).first() if kat.takim_kodu else None

    user_turnir = None
    if kat.turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == kat.turnir_id).first()
        if turnir:
            user_turnir = {
                "id": turnir.id,
                "ad": turnir.ad,
                "senesi": turnir.senesi,
                "wagty": turnir.wagty,
                "karta": turnir.karta,
                "tolekli": turnir.tolekli
            }

    arkadaslar = []
    if kat.takim_kodu:
        arkadaslar = db.query(Katilimci).filter(
            Katilimci.takim_kodu == kat.takim_kodu,
            Katilimci.referans_kodu != ref_code
        ).all()
        arkadaslar = [{"ad": a.ad, "referans_kodu": a.referans_kodu, "admin_onay": a.admin_onay} for a in arkadaslar]

    return {
        "success": True,
        "data": {
            "katilimci": {
                "referans_kodu": kat.referans_kodu,
                "ad": kat.ad,
                "telefon": kat.telefon,
                "pubg_id": kat.pubg_id,
                "payment_phone": kat.payment_phone,
                "takim_kodu": kat.takim_kodu,
                "takim_adi": takim.takim_adi if takim else None,
                "takim_lideri": kat.takim_lideri,
                "odeme_durumu": kat.odeme_durumu,
                "admin_onay": kat.admin_onay,
                "turnir_id": kat.turnir_id,
                "user_turnir": user_turnir,
                "kayit_tarihi": kat.kayit_tarihi.isoformat() if kat.kayit_tarihi else None
            },
            "arkadaslar": arkadaslar
        }
    }

# ---------- ODEME ----------

@app.get("/api/odeme-bilgi")
def api_odeme_bilgi(current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == current_user.referans_kodu).first()
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

@app.post("/api/odeme-yapildi", response_model=SuccessResponse)
@limiter.limit("5/minute")
def api_odeme_yapildi(request: Request, current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    ref = current_user.referans_kodu
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

# ---------- TAKIM ----------

@app.get("/api/takim-bilgi")
def api_takim_bilgi(current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == current_user.referans_kodu).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady")
    return {"success": True, "data": {"katilimci": {"referans_kodu": kat.referans_kodu, "ad": kat.ad, "takim_kodu": kat.takim_kodu}}}

@app.post("/api/takim-olustur", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_takim_olustur(request: Request, data: TakimOlustur, current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    lider_ref = current_user.referans_kodu
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

    logger.info(f"Topar: {kod} - {takim_adi}")
    return {"success": True, "message": "Topar üstünlikli döredildi!", "data": {"takim_kodu": kod}}

@app.post("/api/takima-katil", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_takima_katil(request: Request, data: TakimaKatil, current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    uye_ref = current_user.referans_kodu
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

    msg = f"👥 <b>TOPARA TÄZE AGZA!</b>\n\nTopar: {takim.takim_adi or 'Topar'}\nKod: {takim_kodu}\n👤 {uye['ad']}"
    send_telegram_message(msg)
    logger.info(f"Katil: {takim_kodu} - {uye.ad}")

    return {"success": True, "message": f"Topara goşuldyňyz! ({say+1}/4)"}

# ---------- TURNIR GOSUL ----------

@app.post("/api/turnir-gosul", response_model=SuccessResponse)
@limiter.limit("3/minute")
def api_turnir_gosul(request: Request, data: TurnirGosul, current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    pubg_id = sanitize(data.pubg_id, 20)
    payment_phone = str(data.payment_phone or "").strip()
    tournament_id = sanitize(data.tournament_id or "", 50)
    turnir_id = data.turnir_id

    if not pubg_id or len(pubg_id) < 8 or not pubg_id.isdigit():
        raise HTTPException(status_code=400, detail="PUBG ID diňe san bolmaly (minimum 8)!")

    ref = current_user.referans_kodu

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

# ---------- KATILIMCI API ----------

@app.get("/api/katilimci/me")
def api_katilimci_me(current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    ref = current_user.referans_kodu
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady")

    result = {
        "id": kat.id,
        "referans_kodu": kat.referans_kodu,
        "ad": kat.ad,
        "telefon": kat.telefon,
        "pubg_id": kat.pubg_id,
        "payment_phone": kat.payment_phone,
        "tournament_id": kat.tournament_id,
        "turnir_id": kat.turnir_id,
        "takim_kodu": kat.takim_kodu,
        "takim_lideri": kat.takim_lideri,
        "odeme_durumu": kat.odeme_durumu,
        "admin_onay": kat.admin_onay,
        "kayit_tarihi": kat.kayit_tarihi.isoformat() if kat.kayit_tarihi else None,
        "odeme_tarihi": kat.odeme_tarihi.isoformat() if kat.odeme_tarihi else None,
        "onay_tarihi": kat.onay_tarihi.isoformat() if kat.onay_tarihi else None
    }

    if kat.turnir_id:
        turnir = db.query(Turnir).filter(Turnir.id == kat.turnir_id).first()
        if turnir:
            result["turnir_ady"] = turnir.ad
            result["turnir_senesi"] = turnir.senesi
            result["turnir_wagty"] = turnir.wagty

    return {"success": True, "katilimci": result}

@app.get("/api/katilimci/{ref_code}")
def api_katilimci(ref_code: str, current_user: Katilimci = Depends(get_current_user), db: Session = Depends(get_db)):
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref_code).first()
    if not kat:
        return {"success": False}

    takim = db.query(Takim).filter(Takim.takim_kodu == kat.takim_kodu).first() if kat.takim_kodu else None
    return {
        "success": True,
        "katilimci": {
            "referans_kodu": kat.referans_kodu,
            "ad": kat.ad,
            "telefon": kat.telefon,
            "takim_kodu": kat.takim_kodu,
            "takim_adi": takim.takim_adi if takim else None,
            "admin_onay": kat.admin_onay,
            "turnir_id": kat.turnir_id
        }
    }

# ---------- ADMIN ----------

@app.post("/api/admin-login", response_model=SuccessResponse)
@limiter.limit("5/minute")
def api_admin_login(request: Request, data: AdminLogin):
    sifre = data.sifre

    if not sifre or len(sifre) < 6:
        logger.warning(f"Nadogry login (gysga parol)")
        raise HTTPException(status_code=400, detail="Parol 6 harpdan uly bolmaly!")

    if not verify_admin_password(sifre):
        logger.warning(f"Nadogry admin login")
        raise HTTPException(status_code=400, detail="Parol nädogry!")

    token = create_access_token({"sub": "admin", "type": "admin"})
    logger.info(f"Admin login")
    return {"success": True, "message": "Giriş üstünlikli!", "data": {"access_token": token}}

@app.get("/api/admin-panel")
def api_admin_panel(admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    stats = get_stats(db)

    katilimcilar = db.query(Katilimci).order_by(Katilimci.kayit_tarihi.desc()).all()
    kat_list = []
    for k in katilimcilar:
        takim = db.query(Takim).filter(Takim.takim_kodu == k.takim_kodu).first() if k.takim_kodu else None
        kat_list.append({
            "id": k.id,
            "referans_kodu": k.referans_kodu,
            "ad": k.ad,
            "telefon": k.telefon,
            "pubg_id": k.pubg_id,
            "payment_phone": k.payment_phone,
            "takim_kodu": k.takim_kodu,
            "takim_adi": takim.takim_adi if takim else None,
            "takim_lideri": k.takim_lideri,
            "odeme_durumu": k.odeme_durumu,
            "admin_onay": k.admin_onay,
            "turnir_id": k.turnir_id,
            "kayit_tarihi": k.kayit_tarihi.isoformat() if k.kayit_tarihi else None
        })

    takimlar = db.query(Takim).order_by(Takim.id.desc()).all()
    tak_list = []
    for t in takimlar:
        lider = db.query(Katilimci).filter(Katilimci.referans_kodu == t.lider_referans).first()
        tak_list.append({
            "id": t.id,
            "takim_kodu": t.takim_kodu,
            "takim_adi": t.takim_adi,
            "lider_referans": t.lider_referans,
            "lider_ady": lider.ad if lider else None,
            "uye1_referans": t.uye1_referans,
            "uye2_referans": t.uye2_referans,
            "uye3_referans": t.uye3_referans,
            "durum": t.durum
        })

    turnirler = get_all_turnirler(db)

    return {
        "success": True,
        "data": {
            "stats": stats,
            "katilimcilar": kat_list,
            "takimlar": tak_list,
            "turnir": get_turnir_data(db),
            "bayraklar": get_bayraklar(db),
            "turnirler": turnirler
        }
    }

@app.post("/api/admin-turnir-ekle", response_model=SuccessResponse)
def api_admin_turnir_ekle(data: TurnirCreate, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    ad = sanitize(data.ad, 100)
    senesi = sanitize(data.senesi, 50)
    wagty = sanitize(data.wagty, 50)
    karta = sanitize(data.karta, 50)
    mode = sanitize(data.mode, 20)
    gatnasym = sanitize(data.gatnasym, 100)
    tolek = sanitize(data.tolek, 50)
    tolek_usuly = sanitize(data.tolek_usuly, 100)

    if not all([ad, senesi, wagty, karta]):
        raise HTTPException(status_code=400, detail="Ad, sene, wagt we karta hökmany!")

    now = datetime.utcnow()
    new_turnir = Turnir(
        ad=ad,
        senesi=senesi,
        wagty=wagty,
        karta=karta,
        mode=mode,
        gatnasym=gatnasym,
        tolek=tolek,
        tolek_usuly=tolek_usuly,
        yer_sany=data.yer_sany,
        bayrak_1=sanitize(data.bayrak_1, 100),
        bayrak_2=sanitize(data.bayrak_2, 100),
        bayrak_3=sanitize(data.bayrak_3, 100),
        bayrak_jemi=sanitize(data.bayrak_jemi, 50),
        status=sanitize(data.status, 20),
        tolekli=1 if data.tolekli else 0,
        created_at=now
    )
    db.add(new_turnir)
    db.commit()
    db.refresh(new_turnir)

    logger.info(f"Täze turnir goşuldy: {ad} (tolekli={data.tolekli})")
    return {"success": True, "message": "Turnir üstünlikli goşuldy!"}

@app.post("/api/admin-turnir-guncelle", response_model=SuccessResponse)
def api_admin_turnir_guncelle(data: TurnirUpdate, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    turnir = db.query(Turnir).filter(Turnir.id == data.turnir_id).first()
    if not turnir:
        raise HTTPException(status_code=404, detail="Turnir tapylmady!")

    if data.ad is not None: turnir.ad = sanitize(data.ad, 100)
    if data.senesi is not None: turnir.senesi = sanitize(data.senesi, 50)
    if data.wagty is not None: turnir.wagty = sanitize(data.wagty, 50)
    if data.karta is not None: turnir.karta = sanitize(data.karta, 50)
    if data.mode is not None: turnir.mode = sanitize(data.mode, 20)
    if data.gatnasym is not None: turnir.gatnasym = sanitize(data.gatnasym, 100)
    if data.tolek is not None: turnir.tolek = sanitize(data.tolek, 50)
    if data.tolek_usuly is not None: turnir.tolek_usuly = sanitize(data.tolek_usuly, 100)
    if data.yer_sany is not None: turnir.yer_sany = data.yer_sany
    if data.bayrak_1 is not None: turnir.bayrak_1 = sanitize(data.bayrak_1, 100)
    if data.bayrak_2 is not None: turnir.bayrak_2 = sanitize(data.bayrak_2, 100)
    if data.bayrak_3 is not None: turnir.bayrak_3 = sanitize(data.bayrak_3, 100)
    if data.bayrak_jemi is not None: turnir.bayrak_jemi = sanitize(data.bayrak_jemi, 50)
    if data.status is not None: turnir.status = sanitize(data.status, 20)
    if data.tolekli is not None: turnir.tolekli = 1 if data.tolekli else 0

    db.commit()
    logger.info(f"Turnir üýtgedildi: ID {data.turnir_id}")
    return {"success": True, "message": "Turnir üstünlikli üýtgedildi!"}

@app.post("/api/admin-turnir-sil", response_model=SuccessResponse)
def api_admin_turnir_sil(data: AdminTurnirSil, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    turnir_id = data.turnir_id

    db.query(Katilimci).filter(Katilimci.turnir_id == turnir_id).update({"turnir_id": None})
    db.query(Turnir).filter(Turnir.id == turnir_id).delete()
    db.commit()

    logger.info(f"Turnir pozuldy: ID {turnir_id}")
    return {"success": True, "message": "Turnir üstünlikli pozuldy!"}

@app.post("/api/admin-ayarlari-kaydet", response_model=SuccessResponse)
def api_admin_ayarlari_kaydet(data: AdminAyarlar, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    for key, value in data.ayarlar.items():
        if value is not None:
            set_ayar_db(key, str(value), db)
    logger.info("Ayarlar üýtgedildi")
    return {"success": True, "message": "Ayarlar üstünlikli saklandy!"}

@app.post("/api/admin-onayla", response_model=SuccessResponse)
def api_admin_onayla(data: AdminOnayla, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    ref = data.referans_kodu
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    if not kat.turnir_id:
        raise HTTPException(status_code=400, detail="Katylyjy entek turnira goşulmadyk!")

    now = datetime.utcnow()
    kat.admin_onay = 1
    kat.onay_tarihi = now
    db.commit()

    msg = f"✅ <b>TASSYKLANDY!</b>\n\n👤 {kat.ad}\n🔑 {ref}\n📅 {now.strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(msg)
    logger.info(f"Onay: {ref}")
    return {"success": True, "message": "Katylyjy tassyklandy!"}

@app.post("/api/admin-reddet", response_model=SuccessResponse)
def api_admin_reddet(data: AdminReddet, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    ref = data.referans_kodu
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    kat.admin_onay = 2
    db.commit()

    msg = f"❌ <b>RET EDILDI!</b>\n\n👤 {kat.ad}\n🔑 {ref}"
    send_telegram_message(msg)
    logger.info(f"Red: {ref}")
    return {"success": True, "message": "Katylyjy ret edildi!"}

@app.post("/api/admin-poz", response_model=SuccessResponse)
def api_admin_poz(data: AdminPoz, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    ref = data.referans_kodu
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    if kat.takim_lideri == 1 and kat.takim_kodu:
        db.query(Takim).filter(Takim.takim_kodu == kat.takim_kodu).delete()
        db.query(Katilimci).filter(Katilimci.takim_kodu == kat.takim_kodu).update({
            "takim_kodu": None,
            "takim_lideri": 0
        })
    elif kat.takim_kodu and kat.takim_lideri == 0:
        team = db.query(Takim).filter(Takim.takim_kodu == kat.takim_kodu).first()
        if team:
            if team.uye1_referans == ref:
                team.uye1_referans = None
            elif team.uye2_referans == ref:
                team.uye2_referans = None
            elif team.uye3_referans == ref:
                team.uye3_referans = None

    db.query(Katilimci).filter(Katilimci.referans_kodu == ref).delete()
    db.commit()

    logger.info(f"Pozuldy: {ref}")
    return {"success": True, "message": "Katylyjy pozuldy!"}

@app.get("/api/turnir-detay/{turnir_id}")
def api_turnir_detay(turnir_id: int, admin: bool = Depends(get_current_admin), db: Session = Depends(get_db)):
    turnir = db.query(Turnir).filter(Turnir.id == turnir_id).first()
    if not turnir:
        raise HTTPException(status_code=404, detail="Turnir tapylmady!")
    return {"success": True, "turnir": {
        "id": turnir.id,
        "ad": turnir.ad,
        "senesi": turnir.senesi,
        "wagty": turnir.wagty,
        "karta": turnir.karta,
        "mode": turnir.mode,
        "gatnasym": turnir.gatnasym,
        "tolek": turnir.tolek,
        "tolek_usuly": turnir.tolek_usuly,
        "yer_sany": turnir.yer_sany,
        "bayrak_1": turnir.bayrak_1,
        "bayrak_2": turnir.bayrak_2,
        "bayrak_3": turnir.bayrak_3,
        "bayrak_jemi": turnir.bayrak_jemi,
        "status": turnir.status,
        "tolekli": turnir.tolekli,
        "durum": turnir.durum,
        "created_at": turnir.created_at.isoformat() if turnir.created_at else None
    }}

# ---------- ERROR HANDLERS ----------

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "message": "Sahypa tapylmady"}
    )

@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.error(f"500: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Serwer ýalňyşlygy"}
    )

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc):
    return JSONResponse(
        status_code=429,
        content={"success": False, "message": "Gaty köp synanyşyk!"}
    )
