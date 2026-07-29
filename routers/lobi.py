"""PUBG Lobi Kody Router"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Katilimci, Turnir
from schemas import SuccessResponse
from config import settings

router = APIRouter(prefix="/api", tags=["Lobi Kody"])

# JWT token dogrulamak üçin
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Katilimci:
    """
    Authorization header-dan Bearer token alyp, JWT decode edýär.
    Token-deki 'sub' (user id) bilen database-dan ulanyjy gözleýär.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token nadogry ýa-da wagty gutardy",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(Katilimci).filter(Katilimci.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


@router.get("/lobi-kodu", response_model=SuccessResponse)
async def get_lobi_kodu(
    turnir_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Katilimci = Depends(get_current_user)
):
    """
    Ulanyjynyň turnirine görä lobi kodyny gaýtarýar.
    - Tölegsiz turnir: gatnaşan bolsa kody görkezýär
    - Tölegli turnir: admin_onay == 1 bolsa kody görkezýär
    """
    katilimci = db.query(Katilimci).filter(Katilimci.id == current_user.id).first()
    if not katilimci:
        return SuccessResponse(success=False, message="Ulanyjy tapylmady")
    
    if not turnir_id:
        turnir_id = katilimci.turnir_id
    
    if not turnir_id:
        return SuccessResponse(
            success=False,
            message="Siz entek haýsydyr bir turnira gatnaşmadynyz"
        )
    
    turnir = db.query(Turnir).filter(Turnir.id == turnir_id).first()
    if not turnir:
        return SuccessResponse(success=False, message="Turnir tapylmady")
    
    # Tölegsiz turnir (tolekli == 0)
    if turnir.tolekli == 0:
        return SuccessResponse(
            success=True,
            message="Lobi kody",
            data={
                "lobi_kodu": turnir.lobi_kodu,
                "turnir_ady": turnir.ad,
                "tolekli": False,
                "görkezilýär": True
            }
        )
    
    # Tölegli turnir - admin tassyklamasy gerek
    if katilimci.admin_onay == 1:
        return SuccessResponse(
            success=True,
            message="Lobi kody",
            data={
                "lobi_kodu": turnir.lobi_kodu,
                "turnir_ady": turnir.ad,
                "tolekli": True,
                "onay_durumu": True,
                "görkezilýär": True
            }
        )
    else:
        return SuccessResponse(
            success=False,
            message="Lobi kodyny görmek üçin admin tassyklamasy garaşylýar",
            data={
                "tolekli": True,
                "onay_durumu": False,
                "görkezilýär": False
            }
        )
