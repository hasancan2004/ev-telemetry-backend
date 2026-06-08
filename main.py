import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import init_db, SessionLocal, TelemetryLog

app = FastAPI(title="EV Telemetry Simulator")

@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic modelimize GPS verilerini ekledik
class EVTelemetry(BaseModel):
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
    return {"status": "online", "message": "EV Telemetry Backend is running."}

@app.get("/api/v1/telemetry/history")
def get_telemetry_history(limit: int = 20, db: Session = Depends(get_db)):
    logs = db.query(TelemetryLog).order_by(TelemetryLog.timestamp.desc()).limit(limit).all()
    return logs

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Arabanın başlangıç konumu (Seydişehir merkez civarı)
    vehicle_state = {
        "battery": 85.0,
        "suspension_mode": "Comfort",
        "cabin_temp": 22.0,
        "latitude": 37.4194,
        "longitude": 31.8475
    }

    def save_to_database(telemetry: EVTelemetry):
        db = SessionLocal()
        try:
            db_log = TelemetryLog(
                speed_kmh=telemetry.speed_kmh,
                battery_level_pct=telemetry.battery_level_pct,
                regeneration_kw=telemetry.regeneration_kw,
                cabin_temperature_c=telemetry.cabin_temperature_c,
                suspension_mode=telemetry.suspension_mode,
                tire_pressure_psi=telemetry.tire_pressure_psi,
                latitude=telemetry.latitude,     # DB'ye kaydet
                longitude=telemetry.longitude    # DB'ye kaydet
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
                speed = random.randint(40, 120)
                regen = random.uniform(5.0, 30.0) if speed < 60 else 0.0 
                vehicle_state["battery"] -= random.uniform(0.01, 0.03) 
                
                # SİMÜLASYON: Araba hareket ediyor! (Her saniye konumu çok hafif değiştiriyoruz)
                # Kuzeydoğu yönüne doğru gidiyor gibi düşün
                vehicle_state["latitude"] += 0.0002 
                vehicle_state["longitude"] += 0.0002 
                
                telemetry_data = EVTelemetry(
                    speed_kmh=speed,
                    battery_level_pct=round(vehicle_state["battery"], 2),
                    regeneration_kw=round(regen, 1),
                    cabin_temperature_c=vehicle_state["cabin_temp"],
                    suspension_mode=vehicle_state["suspension_mode"],
                    tire_pressure_psi=round(random.uniform(32.0, 36.0), 1),
                    latitude=round(vehicle_state["latitude"], 5),
                    longitude=round(vehicle_state["longitude"], 5)
                )
                
                await websocket.send_json(telemetry_data.model_dump())
                await asyncio.to_thread(save_to_database, telemetry_data)
                
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    sender_task = asyncio.create_task(send_telemetry())

    try:
        while True:
            client_message = await websocket.receive_json()
            if "suspension_mode" in client_message:
                vehicle_state["suspension_mode"] = client_message["suspension_mode"]
            if "cabin_temp" in client_message:
                vehicle_state["cabin_temp"] = client_message["cabin_temp"]

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error receiving data: {e}")
    finally:
        sender_task.cancel()