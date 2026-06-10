import asyncio
import random
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, TelemetryLog
import joblib # YENİ: Eğitilen modeli yüklemek için ekledik
from typing import List

app = FastAPI(title="EV Fleet Telemetry Simulator")

# ========================================================
# YENİ: YAPAY ZEKA MODELİNİN YÜKLENMESİ
# ========================================================
try:
    ai_model = joblib.load("ev_health_model.pkl")
    print("AI MODEL STATUS: Eğitilmiş yapay zeka modeli başarıyla yüklendi!")
except Exception as e:
    ai_model = None
    print(f"AI MODEL STATUS ERROR: Model yüklenemedi: {e}")

@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic modelimize yapay zekanın üreteceği "maintenance_risk_pct" alanını ekledik
class EVTelemetry(BaseModel):
    vehicle_id: str
    speed_kmh: int
    battery_level_pct: float
    regeneration_kw: float
    cabin_temperature_c: float
    suspension_mode: str
    tire_pressure_psi: float
    latitude: float
    longitude: float
    maintenance_risk_pct: float # YENİ: Yapay zekanın arıza risk tahmini (%)
    eco_score: int # YENİ: Sürücü davranış skoru (0-100)

@app.get("/")
def read_root():
    return {"status": "online", "message": "Fleet Backend with AI Engine is running."}

@app.get("/api/v1/telemetry/history")
def get_telemetry_history(vehicle_id: str = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(TelemetryLog)
    if vehicle_id:
        query = query.filter(TelemetryLog.vehicle_id == vehicle_id)
    logs = query.order_by(TelemetryLog.timestamp.desc()).limit(limit).all()
    return logs

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    fleet_state = {
        "EV-001": {"battery": 85.0, "suspension": "Comfort", "temp": 22.0, "lat": 37.8746, "lng": 32.4933, "active": True},
        "EV-002": {"battery": 42.5, "suspension": "Sport", "temp": 20.0, "lat": 37.8800, "lng": 32.4800, "active": True},
        
        # EV-003'ü tam olarak STATION-001 (ZES) istasyonunun bir sokak yanına park ettik!
        "EV-003": {"battery": 15.2, "suspension": "Eco", "temp": 24.0, "lat": 37.8716, "lng": 32.4851, "active": False} 
    }

    def save_to_database(telemetries: List[EVTelemetry]):
        db = SessionLocal()
        try:
            for t in telemetries:
                db_log = TelemetryLog(
                    vehicle_id=t.vehicle_id,
                    speed_kmh=t.speed_kmh,
                    battery_level_pct=t.battery_level_pct,
                    regeneration_kw=t.regeneration_kw,
                    cabin_temperature_c=t.cabin_temperature_c,
                    suspension_mode=t.suspension_mode,
                    tire_pressure_psi=t.tire_pressure_psi,
                    latitude=t.latitude,
                    longitude=t.longitude
                    # Not: Veritabanı şemasını bozmamak için risk yüzdesini şimdilik log tablosuna kaydetmiyoruz, 
                    # sadece soketten anlık canlı veri olarak basacağız.
                )
                db.add(db_log)
            db.commit()
        except Exception as e:
            print(f"Database write error: {e}")
        finally:
            db.close()

    async def send_telemetry():
        try:
            while True:
                fleet_telemetry_list = []
                
                for v_id, state in fleet_state.items():
                    if state["active"]:
                        # Arada sırada yapay zekayı test etmek için kasti anomaliler (yüksek sıcaklık) yaratıyoruz
                        if random.random() < 0.15: 
                            speed = random.randint(95, 120)
                            temp = round(random.uniform(38.0, 52.0), 1) # Sıcaklık fırladı
                            pressure = round(random.uniform(22.0, 26.0), 1) # Lastik iniyor
                        else:
                            speed = random.randint(40, 85)
                            temp = state["temp"]
                            pressure = round(random.uniform(32.0, 35.0), 1)

                        regen = round(random.uniform(5.0, 15.0), 1) if speed < 60 else 0.0
                        state["battery"] -= random.uniform(0.01, 0.03)
                        state["lat"] += random.uniform(-0.0001, 0.0003)
                        state["lng"] += random.uniform(-0.0001, 0.0003)
                    else:
                        speed = 0
                        regen = 0.0
                        temp = state["temp"]
                        pressure = round(random.uniform(33.0, 34.0), 1)
                        if state["battery"] < 100:
                            state["battery"] += 0.05
                    
                    # ========================================================
                    # YENİ: ANLIK YAPAY ZEKA TAHMİNİ (PREDICTION)
                    # ========================================================
                    risk_percentage = 0.0
                    if ai_model:
                        # Modelin eğitildiği sırayla verileri dizi olarak veriyoruz
                        features = [[speed, state["battery"], regen, temp, pressure]]
                        
                        # predict_proba bize [[sağlam_olma_olasılığı, arıza_olma_olasılığı]] döner.
                        # Biz arıza olasılığını ([0][1]) alıp 100 ile çarpıyoruz.
                        probabilities = ai_model.predict_proba(features)
                        risk_percentage = round(probabilities[0][1] * 100, 1)

                    # ========================================================
                    # YENİ: ECO-SCORE (SÜRÜCÜ DAVRANIŞ) HESAPLAMA ALGORİTMASI
                    # ========================================================
                    base_score = 100.0
                    
                    # 1. Hız Cezası (90 km/h üstü her hız için 1.5 puan kır)
                    if speed > 90:
                        base_score -= (speed - 90) * 1.5
                        
                    # 2. Sürüş Modu Etkisi
                    if state["suspension"] == "Sport":
                        base_score -= 15.0 # Agresif mod cezası
                    elif state["suspension"] == "Eco":
                        base_score += 10.0 # Tasarruf modu bonusu
                        
                    # 3. Rejenerasyon (Enerji Geri Kazanım) Bonusu
                    base_score += regen * 1.2
                    
                    # Skoru 0 ile 100 arasında sınırla ve tam sayıya çevir
                    final_eco_score = int(max(0, min(100, base_score)))

                    telemetry = EVTelemetry(
                        vehicle_id=v_id,
                        speed_kmh=speed,
                        battery_level_pct=round(state["battery"], 2),
                        regeneration_kw=round(regen, 1),
                        cabin_temperature_c=temp,
                        suspension_mode=state["suspension"],
                        tire_pressure_psi=pressure,
                        latitude=round(state["lat"], 5),
                        longitude=round(state["lng"], 5),
                        maintenance_risk_pct=risk_percentage, # AI risk puanı eklendi!
                        eco_score=final_eco_score # YENİ: Skoru JSON'a ekliyoruz!
                    )
                    fleet_telemetry_list.append(telemetry)
                
                await websocket.send_json([t.model_dump() for t in fleet_telemetry_list])
                await asyncio.to_thread(save_to_database, fleet_telemetry_list)
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    sender_task = asyncio.create_task(send_telemetry())

    try:
        while True:
            client_message = await websocket.receive_json()
            target_id = client_message.get("vehicle_id", "EV-001")
            
            if target_id in fleet_state:
                if "suspension_mode" in client_message:
                    fleet_state[target_id]["suspension"] = client_message["suspension_mode"]
                if "cabin_temp" in client_message:
                    fleet_state[target_id]["temp"] = client_message["cabin_temp"]

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error receiving data: {e}")
    finally:
        sender_task.cancel()


class ChargingStation(BaseModel):
    id: str
    name: str
    provider: str # ZES, Eşarj, Togg Trugo vb.
    latitude: float
    longitude: float
    is_available: bool

# 2. Konya Çevresindeki Sanal Şarj İstasyonları Verisi
MOCK_STATIONS = [
    {
        "id": "STATION-001",
        "name": "Konya Merkez Hızlı Şarj İstasyonu",
        "provider": "ZES",
        "latitude": 37.8715,
        "longitude": 32.4850,
        "is_available": True
    },
    {
        "id": "STATION-002",
        "name": "Selçuklu Alışveriş Merkezi Şarj Noktası",
        "provider": "Eşarj",
        "latitude": 37.9150,
        "longitude": 32.5020,
        "is_available": True
    },
    {
        "id": "STATION-003",
        "name": "Karatay Sanayi Bölgesi DC İstasyonu",
        "provider": "Trugo",
        "latitude": 37.8620,
        "longitude": 32.5310,
        "is_available": False # Şu an kullanım dışı senaryosu için
    }
]

# 3. REST API Endpoint'i
@app.get("/api/v1/charging-stations", response_model=List[ChargingStation])
def get_charging_stations():
    return MOCK_STATIONS