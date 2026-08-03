"""Magazyn router - UC paketler we Akkauntlar"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import UCPaket, Akkaunt, SatynAlma, Katilimci
from schemas import SuccessResponse, UCPaketCreate, AkkauntCreate, SatynAlmaCreate
from auth import get_current_user, get_current_admin
from utils import sanitize, send_telegram_message

router = APIRouter(tags=["Magazyn"])
logger = logging.getLogger(__name__)


# ========== UC PAKETLER ==========

@router.get("/api/uc-paketler", response_model=SuccessResponse)
def api_uc_paketler(db: Session = Depends(get_db)):
    """Ähli aktiv UC paketlerini getir"""
    paketler = db.query(UCPaket).filter(UCPaket.aktiw == 1).order_by(UCPaket.siralama.asc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "ad": p.ad,
                "uc_sany": p.uc_sany,
                "bahasy": p.bahasy,
                "surat": p.surat,
                "siralama": p.siralama
            }
            for p in paketler
        ]
    }


@router.post("/api/admin/uc-paket-ekle", response_model=SuccessResponse)
def api_uc_paket_ekle(data: UCPaketCreate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: Täze UC paket goş"""
    paket = UCPaket(
        ad=sanitize(data.ad, 100),
        uc_sany=data.uc_sany,
        bahasy=data.bahasy,
        surat=sanitize(data.surat, 500) if data.surat else None,
        siralama=data.siralama
    )
    db.add(paket)
    db.commit()
    db.refresh(paket)
    logger.info(f"UC paket goşuldy: {paket.ad}")
    return {"success": True, "message": "UC paket goşuldy!", "data": {"id": paket.id}}


@router.post("/api/admin/uc-paket-sil/{paket_id}", response_model=SuccessResponse)
def api_uc_paket_sil(paket_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: UC paket poz"""
    paket = db.query(UCPaket).filter(UCPaket.id == paket_id).first()
    if not paket:
        raise HTTPException(status_code=404, detail="Paket tapylmady!")
    db.delete(paket)
    db.commit()
    return {"success": True, "message": "UC paket pozuldy!"}


# ========== AKKAUNTLAR ==========

@router.get("/api/akkauntlar", response_model=SuccessResponse)
def api_akkauntlar(db: Session = Depends(get_db)):
    """Ähli satylyk akkauntlary getir"""
    akkauntlar = db.query(Akkaunt).filter(Akkaunt.aktiw == 1, Akkaunt.satyldy == 0).order_by(Akkaunt.created_at.desc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "ad": a.ad,
                "level": a.level,
                "rank": a.rank,
                "skin_sany": a.skin_sany,
                "taryh": a.taryh,
                "bahasy": a.bahasy,
                "suratlar": json.loads(a.suratlar) if a.suratlar else []
            }
            for a in akkauntlar
        ]
    }


@router.post("/api/admin/akkaunt-ekle", response_model=SuccessResponse)
def api_akkaunt_ekle(data: AkkauntCreate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: Täze akkaunt goş"""
    akkaunt = Akkaunt(
        ad=sanitize(data.ad, 200),
        level=data.level,
        rank=sanitize(data.rank, 50) if data.rank else None,
        skin_sany=data.skin_sany,
        taryh=sanitize(data.taryh, 2000) if data.taryh else None,
        bahasy=data.bahasy,
        suratlar=data.suratlar if data.suratlar else None
    )
    db.add(akkaunt)
    db.commit()
    db.refresh(akkaunt)
    logger.info(f"Akkaunt goşuldy: {akkaunt.ad}")
    return {"success": True, "message": "Akkaunt goşuldy!", "data": {"id": akkaunt.id}}


@router.post("/api/admin/akkaunt-sil/{akkaunt_id}", response_model=SuccessResponse)
def api_akkaunt_sil(akkaunt_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: Akkaunt poz"""
    akkaunt = db.query(Akkaunt).filter(Akkaunt.id == akkaunt_id).first()
    if not akkaunt:
        raise HTTPException(status_code=404, detail="Akkaunt tapylmady!")
    db.delete(akkaunt)
    db.commit()
    return {"success": True, "message": "Akkaunt pozuldy!"}


# ========== SATYN ALMA ==========

@router.post("/api/satyn-al", response_model=SuccessResponse)
def api_satyn_al(data: SatynAlmaCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ulanyjy: UC ýa-da akkaunt satyn al"""
    ref = current_user.get("sub")
    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    product_type = data.product_type
    product_id = data.product_id

    if product_type == "uc":
        product = db.query(UCPaket).filter(UCPaket.id == product_id, UCPaket.aktiw == 1).first()
        if not product:
            raise HTTPException(status_code=404, detail="UC paket tapylmady!")
        bahasy = product.bahasy
        ady = product.ad
    else:
        product = db.query(Akkaunt).filter(Akkaunt.id == product_id, Akkaunt.aktiw == 1, Akkaunt.satyldy == 0).first()
        if not product:
            raise HTTPException(status_code=404, detail="Akkaunt tapylmady ýa-da eýýäm satyldy!")
        bahasy = product.bahasy
        ady = product.ad
        product.satyldy = 1

    satyn_alma = SatynAlma(
        katilimci_ref=ref,
        product_type=product_type,
        product_id=product_id,
        bahasy=bahasy,
        status="pending",
        telegram=sanitize(data.telegram, 100) if data.telegram else None,
        pubg_id=sanitize(data.pubg_id, 50) if data.pubg_id else None
    )
    db.add(satyn_alma)
    db.commit()
    db.refresh(satyn_alma)

    msg = (
        f"🛒 <b>TÄZE SARGYT!</b>

"
        f"👤 {kat.ad}
"
        f"🔑 {ref}
"
        f"📦 {ady}
"
        f"💰 {bahasy} TMT
"
        f"📱 Telegram: {data.telegram or 'Ýok'}
"
        f"🎮 PUBG ID: {data.pubg_id or 'Ýok'}"
    )
    send_telegram_message(msg)
    logger.info(f"Satyn alma: {ref} -> {ady}")

    return {
        "success": True,
        "message": "Sargyt üstünlikli ugradyldy! Admin tassyklamasyndan soň üstünlikli bolar.",
        "data": {"sargyt_id": satyn_alma.id, "status": "pending"}
    }


@router.get("/api/menin-sargytlarym", response_model=SuccessResponse)
def api_menin_sargytlarym(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ulanyjynyň sargytlary"""
    ref = current_user.get("sub")
    sargytlar = db.query(SatynAlma).filter(SatynAlma.katilimci_ref == ref).order_by(SatynAlma.created_at.desc()).all()

    result = []
    for s in sargytlar:
        if s.product_type == "uc":
            product = db.query(UCPaket).filter(UCPaket.id == s.product_id).first()
        else:
            product = db.query(Akkaunt).filter(Akkaunt.id == s.product_id).first()

        result.append({
            "id": s.id,
            "product_type": s.product_type,
            "product_ady": product.ad if product else "N/A",
            "bahasy": s.bahasy,
            "status": s.status,
            "pubg_id": s.pubg_id,
            "telegram": s.telegram,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return {"success": True, "data": result}


# ========== ADMIN SARGYTLAR ==========

@router.get("/api/admin/sargytlar", response_model=SuccessResponse)
def api_admin_sargytlar(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: Ähli sargytlary gör"""
    sargytlar = db.query(SatynAlma).order_by(SatynAlma.created_at.desc()).all()

    result = []
    for s in sargytlar:
        kat = db.query(Katilimci).filter(Katilimci.referans_kodu == s.katilimci_ref).first()
        if s.product_type == "uc":
            product = db.query(UCPaket).filter(UCPaket.id == s.product_id).first()
        else:
            product = db.query(Akkaunt).filter(Akkaunt.id == s.product_id).first()

        result.append({
            "id": s.id,
            "katilimci_ref": s.katilimci_ref,
            "katilimci_ady": kat.ad if kat else "N/A",
            "product_type": s.product_type,
            "product_ady": product.ad if product else "N/A",
            "bahasy": s.bahasy,
            "status": s.status,
            "pubg_id": s.pubg_id,
            "telegram": s.telegram,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return {"success": True, "data": result}


@router.post("/api/admin/sargyt-tassykla/{sargyt_id}", response_model=SuccessResponse)
def api_sargyt_tassykla(sargyt_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: Sargyt tassykla"""
    sargyt = db.query(SatynAlma).filter(SatynAlma.id == sargyt_id).first()
    if not sargyt:
        raise HTTPException(status_code=404, detail="Sargyt tapylmady!")

    sargyt.status = "completed"
    sargyt.completed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Sargyt tassyklandy: {sargyt_id}")
    return {"success": True, "message": "Sargyt tassyklandy!"}


@router.post("/api/admin/sargyt-yzyna/{sargyt_id}", response_model=SuccessResponse)
def api_sargyt_yzyna(sargyt_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Admin: Sargyt ýzyna çek"""
    sargyt = db.query(SatynAlma).filter(SatynAlma.id == sargyt_id).first()
    if not sargyt:
        raise HTTPException(status_code=404, detail="Sargyt tapylmady!")

    if sargyt.product_type == "akkaunt":
        akkaunt = db.query(Akkaunt).filter(Akkaunt.id == sargyt.product_id).first()
        if akkaunt:
            akkaunt.satyldy = 0

    sargyt.status = "cancelled"
    db.commit()

    logger.info(f"Sargyt ýzyna çekildi: {sargyt_id}")
    return {"success": True, "message": "Sargyt ýzyna çekildi!"}
