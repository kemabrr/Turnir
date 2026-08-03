"""Database modelleri - SQLAlchemy 2.0"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, Float
from datetime import datetime
from database import Base

class Katilimci(Base):
    __tablename__ = "katilimcilar"
    __table_args__ = (
        Index("idx_katilimci_ref", "referans_kodu"),
        Index("idx_katilimci_telefon", "telefon"),
        Index("idx_katilimci_takim", "takim_kodu"),
        Index("idx_katilimci_pubg", "pubg_id"),
        Index("idx_katilimci_turnir", "turnir_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    referans_kodu = Column(String(20), unique=True, nullable=False)
    ad = Column(String(100), nullable=False)
    telefon = Column(String(20), unique=True, nullable=False)
    parol_hash = Column(String(200), nullable=False)
    pubg_id = Column(String(20))
    payment_phone = Column(String(20))
    tournament_id = Column(String(50))
    turnir_id = Column(Integer, ForeignKey("turnirler.id"))
    ulasim = Column(String(50))
    takim_kodu = Column(String(20))
    takim_lideri = Column(Integer, default=0)
    odeme_durumu = Column(Integer, default=0)
    admin_onay = Column(Integer, default=0)
    kayit_tarihi = Column(DateTime, nullable=False, default=datetime.utcnow)
    odeme_tarihi = Column(DateTime)
    onay_tarihi = Column(DateTime)

class Takim(Base):
    __tablename__ = "takimlar"
    __table_args__ = (Index("idx_takim_kod", "takim_kodu"),)

    id = Column(Integer, primary_key=True, index=True)
    takim_kodu = Column(String(20), unique=True, nullable=False)
    takim_adi = Column(String(50))
    lider_referans = Column(String(20), nullable=False)
    uye1_referans = Column(String(20))
    uye2_referans = Column(String(20))
    uye3_referans = Column(String(20))
    durum = Column(Integer, default=0)

class Turnir(Base):
    __tablename__ = "turnirler"
    __table_args__ = (Index("idx_turnir_status", "status"),)

    id = Column(Integer, primary_key=True, index=True)
    ad = Column(String(100), nullable=False)
    senesi = Column(String(50), nullable=False)
    wagty = Column(String(50), nullable=False)
    karta = Column(String(50), nullable=False)
    mode = Column(String(20), default="squad")
    gatnasym = Column(String(100), nullable=False)
    tolek = Column(String(50), nullable=False)
    tolek_usuly = Column(String(100), nullable=False)
    yer_sany = Column(Integer, default=100)
    bayrak_1 = Column(String(100), default="300 Manat|+ 🏆 Kubok")
    bayrak_2 = Column(String(100), default="150 Manat")
    bayrak_3 = Column(String(100), default="50 Manat")
    bayrak_jemi = Column(String(50), default="500 M")
    status = Column(String(20), default="upcoming")
    tolekli = Column(Integer, default=1)
    durum = Column(Integer, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    lobi_kodu = Column(String(50))

class Ayar(Base):
    __tablename__ = "ayarlar"
    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)


# ========== TÄZE: MAGAZYN MODELLERI ==========

class UCPaket(Base):
    """PUBG UC paketleri"""
    __tablename__ = "uc_paketler"

    id = Column(Integer, primary_key=True, index=True)
    ad = Column(String(100), nullable=False)
    uc_sany = Column(Integer, nullable=False)
    bahasy = Column(Float, nullable=False)
    surat = Column(String(500))
    aktiw = Column(Integer, default=1)
    siralama = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Akkaunt(Base):
    """PUBG satlyk akkauntlar"""
    __tablename__ = "akkauntlar"

    id = Column(Integer, primary_key=True, index=True)
    ad = Column(String(200), nullable=False)
    level = Column(Integer, default=1)
    rank = Column(String(50))
    skin_sany = Column(Integer, default=0)
    taryh = Column(Text)
    bahasy = Column(Float, nullable=False)
    suratlar = Column(Text)
    aktiw = Column(Integer, default=1)
    satyldy = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class SatynAlma(Base):
    """Satyn almalar taryhy"""
    __tablename__ = "satyn_almalar"

    id = Column(Integer, primary_key=True, index=True)
    katilimci_ref = Column(String(20), ForeignKey("katilimcilar.referans_kodu"), nullable=False)
    product_type = Column(String(20), nullable=False)
    product_id = Column(Integer, nullable=False)
    bahasy = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    telegram = Column(String(100))
    pubg_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
