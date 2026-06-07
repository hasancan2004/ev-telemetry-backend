import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="EV Telemetry Simulator")

# Pydantic modelimiz (Kotlin'deki Data Class'ın tam karşılığı)
class EVTelemetry(BaseModel):
    speed_kmh: int
    battery_level_pct: int
    regeneration_kw: float
    cabin_temperature_c: float
    suspension_mode: str
    tire_pressure_psi: float

@app.get("/")
def read_root():
    # REST API için İngilizce durum mesajı
    return {"status": "online", "message": "EV Telemetry Backend is running."}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Başlangıç batarya seviyesi
        battery_level = 85.0


        while True:
            # Simülasyon verileri üretme
            speed = random.randint(40, 120)

            # Araç yavaşlarken (hız düşükken) rejeneratif frenleme devreye girsin
            regen = random.uniform(5.0, 30.0) if speed < 60 else 0.0

            # Batarya her saniye çok ufak miktarda azalsın
            battery -= random.uniform(0.01, 0.03)

            telemetry_data = EVTelemetry(
                speed_kmh=speed,
                battery_level_pct=round(battery, 2),
                regeneration_kw=round(regen, 1),
                cabin_temperature_c = round(random.uniform(20.0, 24.0), 1),
                suspension_mode=random.choice(["Comfort", "Sport", "Eco"]),
                tire_pressure_psi=round(random.uniform(32.0, 36.0), 1)
            )

            # Veriyi JSON formatında istemciye fırlat
            await websocket.send_json(telemetry_data.model_dump())

            # 1 saniye bekle (saniyede 1 veri basar)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        # İstemci (mobil uygulama) bağlantıyı kestiğinde verilecek İngilizce log
        print("Client disconnected from the telemetry stream.")
    except Exception as e:
        # Beklenmeyen bir hata durumunda İngilizce log
        print(f"Connection error: {e}")