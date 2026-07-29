"""Lobi Kody router - Kanallar we Lobi Kody"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Katilimci, Turnir
from schemas import SuccessResponse
from auth import get_current_user
from config import settings

router = APIRouter(tags=["Lobi"])
logger = logging.getLogger(__name__)


@router.get("/api/lobi-kanallar", response_model=SuccessResponse)
def api_lobi_kanallar():
    """Kanallar elmydama açyk - auth gerek dal"""
    return {
        "success": True,
        "data": {
            "text": "Aşaky kanallarda turnir kody paýlaşylar, kody wagtynda bilmek üçin kanallara goşulun",
            "kanallar": [
                {
                    "name": "Telegram",
                    "icon": "telegram",
                    "url": settings.telegram_kanal_url or "#"
                },
                {
                    "name": "IMO",
                    "icon": "imo",
                    "url": settings.imo_kanal_url or "#"
                },
                {
                    "name": "Link",
                    "icon": "link",
                    "url": settings.link_kanal_url or "#"
                }
            ]
        }
    }


@router.get("/api/lobi-kodu", response_model=SuccessResponse)
def api_lobi_kodu(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lobi kody - şertli görkezilýär"""
    ref = user.get("sub")
    if not ref:
        raise HTTPException(status_code=401, detail="Ulanyjy tapylmady!")

    kat = db.query(Katilimci).filter(Katilimci.referans_kodu == ref).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Katylyjy tapylmady!")

    if not kat.turnir_id:
        raise HTTPException(
            status_code=400,
            detail="Siz entek haýsydyr bir turnira gatnaşmadynyz!"
        )

    turnir = db.query(Turnir).filter(Turnir.id == kat.turnir_id).first()
    if not turnir:
        raise HTTPException(status_code=404, detail="Turnir tapylmady!")

    # Tölegsiz turnir -> gönümen görkez
    if turnir.tolekli == 0:
        return {
            "success": True,
            "data": {
                "lobi_kodu": turnir.lobi_kodu or "Heniz bellenmedi",
                "turnir_ady": turnir.ad,
                "görkezilme_sebabi": "tölegsiz"
            }
        }

    # Tölegli turnir -> admin tassyklamasy gerek
    if kat.admin_onay == 1:
        return {
            "success": True,
            "data": {
                "lobi_kodu": turnir.lobi_kodu or "Heniz bellenmedi",
                "turnir_ady": turnir.ad,
                "görkezilme_sebabi": "tassyklandy"
            }
        }
    elif kat.admin_onay == 2:
        raise HTTPException(
            status_code=403,
            detail="Katylyjyňyz ret edildi!"
        )
    else:
        raise HTTPException(
            status_code=403,
            detail="Lobi kody diňe admin tassyklamasyndan soň görkezilýär!"
        )
