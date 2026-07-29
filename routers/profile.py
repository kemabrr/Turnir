"""Profil router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Katilimci, Takim, Turnir
from schemas import SuccessResponse
from auth import get_current_user

router = APIRouter(tags=["Profil"])


@router.get("/api/profil", response_model=SuccessResponse)
def api_profil(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    ref_code = current_user.get("sub")

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


@router.get("/api/katilimci/me")
def api_katilimci_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    ref = current_user.get("sub")
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


@router.get("/api/katilimci/{ref_code}")
def api_katilimci(ref_code: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
