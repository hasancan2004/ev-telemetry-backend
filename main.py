import asyncio
import random
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, TelemetryLog

app = FastAPI(title="EV Fleet Telemetry Simulator")

@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic modelimize "vehicle_id" eklendi
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

@app.get("/")
def read_root():
    return {"status": "online", "message": "Fleet Backend is running."}

@app.get("/api/v1/telemetry/history")
def get_telemetry_history(vehicle_id: str = None, limit: int = 100, db: Session = Depends(get_db)):
    # YENİ: Artık Android bizden geçmişi isterken belirli bir aracın (örn: EV-002) geçmişini isteyebilir
    query = db.query(TelemetryLog)
    if vehicle_id:
        query = query.filter(TelemetryLog.vehicle_id == vehicle_id)
    logs = query.order_by(TelemetryLog.timestamp.desc()).limit(limit).all()
    return logs

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # ==========================================
    # YENİ: FİLO TANIMLAMASI (3 Farklı Araç)
    # ==========================================
    fleet_state = {
        "EV-001": {"battery": 85.0, "suspension": "Comfort", "temp": 22.0, "lat": 37.4194, "lng": 31.8475, "active": True},
        "EV-002": {"battery": 42.5, "suspension": "Sport", "temp": 20.0, "lat": 37.4250, "lng": 31.8500, "active": True},
        "EV-003": {"battery": 15.2, "suspension": "Eco", "temp": 24.0, "lat": 37.4100, "lng": 31.8300, "active": False} # Şarjda olan araç
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
                
                # Filonun içindeki tüm araçları tek tek gezip durumlarını güncelliyoruz
                for v_id, state in fleet_state.items():
                    if state["active"]:
                        speed = random.randint(40, 90)
                        regen = random.uniform(5.0, 15.0) if speed < 60 else 0.0
                        state["battery"] -= random.uniform(0.01, 0.03)
                        state["lat"] += random.uniform(-0.0001, 0.0003)
                        state["lng"] += random.uniform(-0.0001, 0.0003)
                    else:
                        speed = 0
                        regen = 0.0
                        if state["battery"] < 100:
                            state["battery"] += 0.05 # Şarj oluyor
                    
                    telemetry = EVTelemetry(
                        vehicle_id=v_id,
                        speed_kmh=speed,
                        battery_level_pct=round(state["battery"], 2),
                        regeneration_kw=round(regen, 1),
                        cabin_temperature_c=state["temp"],
                        suspension_mode=state["suspension"],
                        tire_pressure_psi=round(random.uniform(32.0, 36.0), 1),
                        latitude=round(state["lat"], 5),
                        longitude=round(state["lng"], 5)
                    )
                    fleet_telemetry_list.append(telemetry)
                
                # KRİTİK DEĞİŞİKLİK: Artık tek bir obje değil, "[" ile başlayan bir "Liste (Array)" fırlatıyoruz!
                await websocket.send_json([t.model_dump() for t in fleet_telemetry_list])
                await asyncio.to_thread(save_to_database, fleet_telemetry_list)
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    sender_task = asyncio.create_task(send_telemetry())

    try:
        while True:
            client_message = await websocket.receive_json()
            # Android'den komut gelirken artık "Hangi araca komut gönderiyoruz?" bilgisini de bekliyoruz
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