import asyncio
import random
import warnings
from contextlib import asynccontextmanager
from typing import List, Optional

import joblib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import SessionLocal, TelemetryLog, engine, Base
from geofence import check_geofence_breach

warnings.filterwarnings("ignore", message="X does not have valid feature names")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("App startup başladı")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tablolar başarıyla oluşturuldu!")
    except Exception as e:
        print(f"Database startup error: {e}")
    yield
    print("App shutdown başladı")

app = FastAPI(title="EV Fleet Telemetry Simulator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    ai_model = joblib.load("ev_health_model.pkl")
    print("AI MODEL STATUS: Eğitilmiş yapay zeka modeli başarıyla yüklendi!")
except Exception as e:
    ai_model = None
    print(f"AI MODEL STATUS ERROR: Model yüklenemedi: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EVTelemetry(BaseModel):
    vehicle_id: str
    vehicle_model: str
    speed_kmh: int
    battery_level_pct: float
    regeneration_kw: float
    cabin_temperature_c: float
    suspension_mode: str
    tire_pressure_psi: float
    latitude: float
    longitude: float
    maintenance_risk_pct: float
    eco_score: int
    estimated_range_km: int
    geofence_breach: bool

# YENİ: Chat isteklerini yakalamak için Pydantic modeli
class ChatRequest(BaseModel):
    message: str

charging_stations_state = {
    "ST1": {"id": "ST1", "name": "Konya ZES Merkezi", "provider": "ZES", "latitude": 37.87, "longitude": 32.48, "is_available": True},
    "ST2": {"id": "ST2", "name": "Eşarj Selçuklu", "provider": "Eşarj", "latitude": 37.89, "longitude": 32.50, "is_available": True}
}

# MİMARİ DÜZELTME: fleet_state artık Global (Tüm endpointler erişebilir)
fleet_state = {
    "EV-001": {"model": "Mercedes EQE", "capacity_kwh": 90.6, "consumption_kwh": 16.5, "battery": 85.0, "suspension": "Comfort", "temp": 22.0, "lat": 37.8746, "lng": 32.4933, "active": True},
    "EV-002": {"model": "Togg T10X", "capacity_kwh": 88.5, "consumption_kwh": 18.5, "battery": 42.5, "suspension": "Sport", "temp": 20.0, "lat": 37.8800, "lng": 32.4800, "active": True},
    "EV-003": {"model": "Skoda Enyaq iV", "capacity_kwh": 77.0, "consumption_kwh": 15.8, "battery": 15.2, "suspension": "Eco", "temp": 24.0, "lat": 39.9334, "lng": 32.8597, "active": False}
}

@app.get("/")
def read_root():
    return {"status": "online", "message": "Fleet Backend with AI Engine is running on Railway!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ev-telemetry-backend"}

@app.get("/api/v1/telemetry/history")
def get_telemetry_history(vehicle_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    try:
        db_query = db.query(TelemetryLog)
        if vehicle_id:
            db_query = db_query.filter(TelemetryLog.vehicle_id == vehicle_id)
        logs = db_query.order_by(TelemetryLog.timestamp.desc()).limit(limit).all()
        return logs
    except Exception as e:
        print(f"Telemetry history error: {e}")
        return []

@app.get("/api/v1/charging-stations")
def get_charging_stations():
    return list(charging_stations_state.values())

@app.post("/api/v1/charging-stations/{station_id}/reserve")
def reserve_station(station_id: str):
    if station_id in charging_stations_state:
        if charging_stations_state[station_id]["is_available"]:
            charging_stations_state[station_id]["is_available"] = False
            return {"status": "success", "message": f"{station_id} rezerve edildi."}
        else:
            return {"status": "error", "message": "İstasyon zaten dolu!"}
    return {"status": "error", "message": "İstasyon bulunamadı."}

@app.get("/api/v1/analytics")
def get_analytics(db: Session = Depends(get_db)):
    try:
        total_logs = db.query(func.count(TelemetryLog.id)).scalar() or 0
        total_energy = round(total_logs * 0.05, 1)
        avg_eco = db.query(func.avg(TelemetryLog.eco_score)).scalar() or 100
        critical_count = db.query(func.count(TelemetryLog.id)).filter(TelemetryLog.maintenance_risk_pct >= 75.0).scalar() or 0

        return {
            "kpi": {
                "total_energy_kwh": total_energy,
                "avg_eco_score": int(avg_eco),
                "critical_risk_count": critical_count
            }
        }
    except Exception as e:
        print(f"Analytics query error: {e}")
        return {"kpi": {"total_energy_kwh": 0.0, "avg_eco_score": 0, "critical_risk_count": 0}}

# YENİ: Akıllı Filo Asistanı Endpoint'i
@app.post("/api/v1/chat")
def fleet_assistant_chat(request: ChatRequest):
    msg = request.message.lower()
    
    # NLP Simülasyonu: Gelen mesaja göre anlık state'i tarayıp cevap üretir
    if "şarj" in msg or "batarya" in msg:
        low_batt_vehicles = [v for v, data in fleet_state.items() if data["battery"] < 20.0]
        if low_batt_vehicles:
            response = f"Şu araçların şarjı %20'nin altında ve acil şarja yönlendirilmeli: {', '.join(low_batt_vehicles)}."
        else:
            response = "Şu an tüm araçların batarya seviyesi optimal durumda, şarja acil ihtiyaç duyan araç bulunmuyor."
    elif "durum" in msg or "özet" in msg or "aktif" in msg:
        active_count = sum(1 for v in fleet_state.values() if v["active"])
        response = f"Filomuzda toplam {len(fleet_state)} araç bulunuyor. Şu an {active_count} tanesi aktif operasyonda."
    elif "risk" in msg or "bakım" in msg or "arıza" in msg:
        response = "Yapay zeka analizlerine göre şu an filoda anlık olarak acil bakıma muhtaç kritik bir araç görünmüyor. Ancak arka planda motor sıcaklıklarını ve rejeneratif frenleri taramaya devam ediyorum."
    else:
        response = "Merhaba! Ben Filo Yapay Zeka Asistanıyım. Bana 'Hangi araçların şarja ihtiyacı var?', 'Filonun durumu ne?' veya 'Riskli araç var mı?' gibi sorular sorabilirsiniz."
        
    return {"reply": response}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")

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
                    longitude=t.longitude,
                    maintenance_risk_pct=t.maintenance_risk_pct,
                    eco_score=t.eco_score
                )
                db.add(db_log)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Database write error: {e}")
        finally:
            db.close()

    async def send_telemetry():
        try:
            while True:
                fleet_telemetry_list = []
                for v_id, state in fleet_state.items():
                    speed = random.randint(40, 85)
                    regen = round(random.uniform(5.0, 15.0), 1)
                    state["battery"] -= random.uniform(0.01, 0.03)
                    if state["battery"] < 0: state["battery"] = 0
                    risk_percentage = 0.0

                    if ai_model:
                        try:
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                features = [[speed, state["battery"], regen, state["temp"], 33.0]]
                                risk_percentage = round(ai_model.predict_proba(features)[0][1] * 100, 1)
                        except Exception as e:
                            risk_percentage = 0.0

                    telemetry = EVTelemetry(vehicle_id=v_id, vehicle_model=state["model"], speed_kmh=speed, battery_level_pct=round(state["battery"], 2), regeneration_kw=regen, cabin_temperature_c=state["temp"], suspension_mode=state["suspension"], tire_pressure_psi=33.0, latitude=state["lat"], longitude=state["lng"], maintenance_risk_pct=risk_percentage, eco_score=85, estimated_range_km=350, geofence_breach=check_geofence_breach(state["lat"], state["lng"]))
                    fleet_telemetry_list.append(telemetry)

                await websocket.send_json([t.model_dump() for t in fleet_telemetry_list])
                await asyncio.to_thread(save_to_database, fleet_telemetry_list)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    sender_task = asyncio.create_task(send_telemetry())

    try:
        while True:
            try:
                data = await websocket.receive_json()
                if data.get("action") == "set_suspension":
                    target_vehicle = data.get("vehicle_id")
                    new_mode = data.get("value")
                    if target_vehicle in fleet_state:
                        fleet_state[target_vehicle]["suspension"] = new_mode
            except WebSocketDisconnect:
                break
            except Exception:
                break
    finally:
        sender_task.cancel()
        print("WebSocket connection closed")