from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./ev_telemetry.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    speed_kmh = Column(Integer, nullable=False)
    battery_level_pct = Column(Float, nullable=False)
    regeneration_kw = Column(Float, nullable=False)
    cabin_temperature_c = Column(Float, nullable=False)
    suspension_mode = Column(String, nullable=False)
    tire_pressure_psi = Column(Float, nullable=False)
    
    # ==========================================
    # YENİ EKLENEN GPS KOLONLARI
    # ==========================================
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)