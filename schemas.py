"""Pydantic schemas (JSON formatlary)"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ========== AUTH ==========
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserLogin(BaseModel):
    telefon: str
    parol: str

class UserCreate(BaseModel):
    ad: str = Field(..., min_length=2, max_length=100)
    telefon: str
    parol: str = Field(..., min_length=6)
    parol_tekrar: str

# ========== KATILIMCI ==========
class KatilimciResponse(BaseModel):
    id: int
    referans_kodu: str
    ad: str
    telefon: str
    pubg_id: Optional[str] = None
    payment_phone: Optional[str] = None
    tournament_id: Optional[str] = None
    turnir_id: Optional[int] = None
    takim_kodu: Optional[str] = None
    takim_lideri: int = 0
    odeme_durumu: int = 0
    admin_onay: int = 0
    kayit_tarihi: datetime
    odeme_tarihi: Optional[datetime] = None
    onay_tarihi: Optional[datetime] = None

    class Config:
        from_attributes = True

class KatilimciMeResponse(BaseModel):
    success: bool
    katilimci: Optional[dict] = None
    message: Optional[str] = None

# ========== TAKIM ==========
class TakimOlustur(BaseModel):
    takim_adi: str = Field(..., min_length=2, max_length=50)

class TakimaKatil(BaseModel):
    takim_kodu: str

class TakimResponse(BaseModel):
    id: int
    takim_kodu: str
    takim_adi: Optional[str] = None
    lider_referans: str
    uye1_referans: Optional[str] = None
    uye2_referans: Optional[str] = None
    uye3_referans: Optional[str] = None
    durum: int = 0

    class Config:
        from_attributes = True

# ========== TURNIR ==========
class TurnirCreate(BaseModel):
    ad: str
    senesi: str
    wagty: str
    karta: str
    mode: str = "squad"
    gatnasym: str
    tolek: str
    tolek_usuly: str
    yer_sany: int = 100
    bayrak_1: str = "300 Manat|+ 🏆 Kubok"
    bayrak_2: str = "150 Manat"
    bayrak_3: str = "50 Manat"
    bayrak_jemi: str = "500 M"
    status: str = "upcoming"
    tolekli: bool = True

class TurnirUpdate(BaseModel):
    turnir_id: int
    ad: Optional[str] = None
    senesi: Optional[str] = None
    wagty: Optional[str] = None
    karta: Optional[str] = None
    mode: Optional[str] = None
    gatnasym: Optional[str] = None
    tolek: Optional[str] = None
    tolek_usuly: Optional[str] = None
    yer_sany: Optional[int] = None
    bayrak_1: Optional[str] = None
    bayrak_2: Optional[str] = None
    bayrak_3: Optional[str] = None
    bayrak_jemi: Optional[str] = None
    status: Optional[str] = None
    tolekli: Optional[bool] = None

class TurnirResponse(BaseModel):
    id: int
    ad: str
    senesi: str
    wagty: str
    karta: str
    mode: str
    gatnasym: str
    tolek: str
    tolek_usuly: str
    yer_sany: int
    bayrak_1: str
    bayrak_2: str
    bayrak_3: str
    bayrak_jemi: str
    status: str
    tolekli: int
    durum: int
    created_at: datetime
    onaylanan: int = 0
    galan: int = 0

    class Config:
        from_attributes = True

# ========== ODEME ==========
class OdemeYapildi(BaseModel):
    pass

# ========== TURNIR GOSUL ==========
class TurnirGosul(BaseModel):
    pubg_id: str
    payment_phone: Optional[str] = ""
    tournament_id: Optional[str] = ""
    turnir_id: Optional[int] = None

# ========== ADMIN ==========
class AdminLogin(BaseModel):
    sifre: str = Field(..., min_length=6)

class AdminOnayla(BaseModel):
    referans_kodu: str

class AdminReddet(BaseModel):
    referans_kodu: str

class AdminPoz(BaseModel):
    referans_kodu: str

class AdminTurnirSil(BaseModel):
    turnir_id: int

class AdminAyarlar(BaseModel):
    ayarlar: dict

# ========== STATS ==========
class StatsResponse(BaseModel):
    toplam: int
    odeme_yapan: int
    onaylanan: int
    yer_sany: int
    galan: int

# ========== BAYRAKLAR ==========
class BayrakResponse(BaseModel):
    bir: dict
    iki: dict
    uc: dict
    jemi: str

# ========== RESPONSE ==========
class SuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
