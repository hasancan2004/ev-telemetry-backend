from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# SQLite veritabanı dosyasının adı ve bağlantı adresi
DATABASE_URL = "sqlite:///./ev_telemetry.db"

# Veritabanı motorunu ayağa kaldırıyoruz
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Oturum (Session) fabrikasını kuruyoruz
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modellerimizin türeyeceği temel sınıf
Base = declarative_base()

# Veritabanında oluşturulacak olan tablonun şeması (Model)
class TelemetryLog(Base):
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    speed_kmh = Column(Integer, nullable=False)
    battery_level_pct = Column(Float, nullable=False)
    regeneration_kw = Column(Float, nullable=False)
    cabin_temperature_c = Column(Float, nullable=False)
    suspension_mode = Column(String, nullable=False)
    tire_pressure_psi = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow) # Verinin kaydedildiği an

# Tabloları otomatik olarak oluşturacak fonksiyon
def init_db():
    Base.metadata.create_all(bind=engine)

