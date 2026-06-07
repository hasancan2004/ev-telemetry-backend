import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="EV Telemetry Simulator")

class EVTelemetry(BaseModel):
    speed_kmh: int
    battery_level_pct: float
    regeneration_kw: float
    cabin_temperature_c: float
    suspension_mode: str
    tire_pressure_psi: float

@app.get("/")
def read_root():
    return {"status": "online", "message": "EV Telemetry Backend is running."}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Aracın dışarıdan müdahale edilebilir anlık durumu (State)
    vehicle_state = {
        "battery": 85.0,
        "suspension_mode": "Comfort",
        "cabin_temp": 22.0
    }

    # 1. GÖREV: Sürekli veri fırlatan asenkron döngü
    async def send_telemetry():
        try:
            while True:
                speed = random.randint(40, 120)
                regen = random.uniform(5.0, 30.0) if speed < 60 else 0.0 
                vehicle_state["battery"] -= random.uniform(0.01, 0.03) 
                
                telemetry_data = EVTelemetry(
                    speed_kmh=speed,
                    battery_level_pct=round(vehicle_state["battery"], 2),
                    regeneration_kw=round(regen, 1),
                    cabin_temperature_c=vehicle_state["cabin_temp"],
                    suspension_mode=vehicle_state["suspension_mode"],
                    tire_pressure_psi=round(random.uniform(32.0, 36.0), 1)
                )
                await websocket.send_json(telemetry_data.model_dump())
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    # Veri gönderme işini (Task) arka planda başlatıyoruz
    sender_task = asyncio.create_task(send_telemetry())

    try:
        # 2. GÖREV: İstemciden (Mobil/Postman) gelen komutları dinleyen döngü
        while True:
            # Dışarıdan gelen JSON formatındaki komutu bekle ve yakala
            client_message = await websocket.receive_json()
            print(f"Received command from client: {client_message}")
            
            # Gelen komutları işle ve aracın durumunu anında güncelle
            if "suspension_mode" in client_message:
                vehicle_state["suspension_mode"] = client_message["suspension_mode"]
                print(f"Suspension changed to: {vehicle_state['suspension_mode']}")
                
            if "cabin_temp" in client_message:
                vehicle_state["cabin_temp"] = client_message["cabin_temp"]
                print(f"Cabin temp changed to: {vehicle_state['cabin_temp']}")

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error receiving data: {e}")
    finally:
        # İstemci bağlantıyı kestiğinde arka planda çalışan veri gönderme görevini de iptal et
        sender_task.cancel()