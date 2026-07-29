"""Admin router"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi.util import get_remote_address
from slowapi import Limiter

from database import get_db
from models import Katilimci, Takim, Turnir
from schemas import SuccessResponse, AdminLogin, AdminOnayla, AdminReddet, AdminPoz, AdminTurnirSil, AdminAyarlar, TurnirCreate, TurnirUpdate
from auth import get_current_admin, verify_admin_password, create_access_token
from utils import sanitize, send_telegram_message, get_stats, get_turnir_data, get_bayraklar, get_all_turnirler, set_ayar_db

router = APIRouter(tags=["Admin"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/api/admin-login", response_model=SuccessResponse)
@limiter.limit("5/minute")
def api_admin_login(request: Request, data: AdminLogin):
    sifre = data.sifre

    if not sifre or len(sifre) < 6:
        logger.warning("Nadogry login (gysga parol)")
        raise HTTPException(status_code=400, detail="Parol 6 harpdan uly bolmaly!")

    if not verify_admin_password(sifre):
        logger.warning("Nadogry admin login")
        raise HTTPException(status_code=400, detail="Parol nädogry!")

    token = create_access_token({"sub": "admin", "type": "admin", "is_admin": True})
    logger.info("Admin login")
    return {"success": True, "message": "Giriş üstünlikli!", "data": {"access_token": token}}


@router.get("/api/admin-panel")
def api_admin_panel(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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


@router.post("/api/admin-turnir-ekle", response_model=SuccessResponse)
def api_admin_turnir_ekle(data: TurnirCreate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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
        created_at=now,
        # TÄZE
        lobi_kodu=sanitize(data.lobi_kodu, 50) if data.lobi_kodu else None
    )
    db.add(new_turnir)
    db.commit()
    db.refresh(new_turnir)

    logger.info(f"Täze turnir goşuldy: {ad} (tolekli={data.tolekli})")
    return {"success": True, "message": "Turnir üstünlikli goşuldy!"}


@router.post("/api/admin-turnir-guncelle", response_model=SuccessResponse)
def api_admin_turnir_guncelle(data: TurnirUpdate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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
    # TÄZE
    if data.lobi_kodu is not None: turnir.lobi_kodu = sanitize(data.lobi_kodu, 50)

    db.commit()
    logger.info(f"Turnir üýtgedildi: ID {data.turnir_id}")
    return {"success": True, "message": "Turnir üstünlikli üýtgedildi!"}


@router.post("/api/admin-turnir-sil", response_model=SuccessResponse)
def api_admin_turnir_sil(data: AdminTurnirSil, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    turnir_id = data.turnir_id

    db.query(Katilimci).filter(Katilimci.turnir_id == turnir_id).update({"turnir_id": None})
    db.query(Turnir).filter(Turnir.id == turnir_id).delete()
    db.commit()

    logger.info(f"Turnir pozuldy: ID {turnir_id}")
    return {"success": True, "message": "Turnir üstünlikli pozuldy!"}


@router.post("/api/admin-ayarlari-kaydet", response_model=SuccessResponse)
def api_admin_ayarlari_kaydet(data: AdminAyarlar, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    for key, value in data.ayarlar.items():
        if value is not None:
            set_ayar_db(key, str(value), db)
    logger.info("Ayarlar üýtgedildi")
    return {"success": True, "message": "Ayarlar üstünlikli saklandy!"}


@router.post("/api/admin-onayla", response_model=SuccessResponse)
def api_admin_onayla(data: AdminOnayla, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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


@router.post("/api/admin-reddet", response_model=SuccessResponse)
def api_admin_reddet(data: AdminReddet, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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


@router.post("/api/admin-poz", response_model=SuccessResponse)
def api_admin_poz(data: AdminPoz, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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


@router.get("/api/turnir-detay/{turnir_id}")
def api_turnir_detay(turnir_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
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
        "created_at": turnir.created_at.isoformat() if turnir.created_at else None,
        # TÄZE
        "lobi_kodu": turnir.lobi_kodu
    }}
