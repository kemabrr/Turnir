"""Ortak kömekçi funksiýalar"""
import os
import re
import random
import string
import logging
import requests
from html import escape as html_escape
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from config import settings
from models import Katilimci, Takim, Turnir, Ayar

logger = logging.getLogger(__name__)


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
    """Düýp Telegram Bot API-a sorgy ugradýar"""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN ýa-da TELEGRAM_CHAT_ID boş! Habar gitmedi.")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=15
        )
        
        if response.status_code == 200:
            logger.info("Telegram habar ugradyldy")
            return True
        else:
            logger.error(f"Telegram error {response.status_code}: {response.text}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Telegram baglanyşyk ýalňyşlygy: {e}")
        return False


def send_telegram_photo(photo_bytes: bytes, filename: str, caption: str = "") -> bool:
    """Telegram Bot API-a surat (screenshot) ugradýar"""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN ýa-da TELEGRAM_CHAT_ID boş! Surat gitmedi.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            },
            files={
                "photo": (filename or "skrinshot.jpg", photo_bytes)
            },
            timeout=20
        )

        if response.status_code == 200:
            logger.info("Telegram surat ugradyldy")
            return True
        else:
            logger.error(f"Telegram photo error {response.status_code}: {response.text}")
            return False

    except requests.RequestException as e:
        logger.error(f"Telegram surat baglanyşyk ýalňyşlygy: {e}")
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
            "toplam": stats["toplam"],
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
