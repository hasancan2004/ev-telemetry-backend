from datetime import datetime
import os

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base


# Railway'de DATABASE_URL okunur, localde yoksa SQLite kullanılır.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ev_telemetry.db")

# Railway bazen postgres:// verebilir, SQLAlchemy için postgresql:// yapıyoruz.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# SQLite ve PostgreSQL için ayrı engine ayarı
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5}
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)

    vehicle_id = Column(String, nullable=False, index=True)

    speed_kmh = Column(Integer, nullable=False)
    battery_level_pct = Column(Float, nullable=False)
    regeneration_kw = Column(Float, nullable=False)
    cabin_temperature_c = Column(Float, nullable=False)
    suspension_mode = Column(String, nullable=False)
    tire_pressure_psi = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)

    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)