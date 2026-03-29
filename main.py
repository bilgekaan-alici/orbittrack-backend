import math
import random
import time
import json
import asyncio
import io
import csv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import searoute as sr 

app = FastAPI(title="OrbitTrack AI Global v4.3 - Pro")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PORTS = [
    {"name": "Rotterdam", "coords": [51.94, 4.12]},
    {"name": "Hamburg", "coords": [53.53, 9.93]},
    {"name": "Lagos", "coords": [6.44, 3.36]},
    {"name": "Cape Town", "coords": [-33.91, 18.43]},
    {"name": "Mersin", "coords": [36.79, 34.63]},
    {"name": "Barcelona", "coords": [41.34, 2.16]},
    {"name": "London", "coords": [51.51, 0.49]}
]

COMPANIES = [
    {"name": "Maersk", "color": "#00ced1"}, {"name": "MSC Mediterranean", "color": "#f59e0b"},
    {"name": "CMA CGM", "color": "#3b82f6"}, {"name": "TR Freight AI", "color": "#a855f7"}
]

vessels = []
for i in range(60):
    p1, p2 = random.sample(PORTS, 2)
    co = random.choice(COMPANIES)
    
    inventory = []
    for _ in range(random.randint(3, 10)):
        inventory.append({
            "id": f"UNIT-{random.randint(10000, 99999)}",
            "type": random.choice(["Teknoloji", "Gıda", "Tehlikeli Madde", "Lüks Araç"]),
            "risk": random.choice(["Düşük", "Orta", "Yüksek"])
        })

    try:
        path = sr.searoute([p1["coords"][1], p1["coords"][0]], [p2["coords"][1], p2["coords"][0]])['geometry']['coordinates']
        sea_path = [[c[1], c[0]] for c in path]
    except:
        sea_path = [p1["coords"], p2["coords"]]

    vessels.append({
        "id": f"IMO-{random.randint(9000000, 9999999)}",
        "name": f"{random.choice(['Ocean', 'Pacific', 'Global'])} {i}",
        "company": co["name"],
        "color": co["color"],
        "full_path": sea_path,
        "dest": p2["name"],
        "speed": random.uniform(18, 28),
        "total_teu": sum(random.randint(500, 2000) for _ in range(5)),
        "inventory": inventory,
        "t": random.random(),
        "step": random.uniform(0.0005, 0.0015)
    })

def compute_telemetry():
    active = []
    for v in vessels:
        v["t"] += v["step"]
        if v["t"] >= 1: v["t"] = 0
        
        idx = int(v["t"] * (len(v["full_path"])-1))
        frac = (v["t"] * (len(v["full_path"])-1)) - idx
        p1, p2 = v["full_path"][idx], v["full_path"][idx+1]
        
        lat = p1[0] + (p2[0]-p1[0]) * frac
        lon = p1[1] + (p2[1]-p1[1]) * frac
        
        status = "active"
        if idx % 20 == 0 and random.random() > 0.85: status = "weather_risk"
        elif random.random() > 0.99: status = "danger"

        active.append({
            "id": v["id"], "name": v["name"], "company": v["company"],
            "color": v["color"], "lat": lat, "lon": lon,
            "speed": round(v["speed"], 1), "teu": v["total_teu"],
            "dest": v["dest"], "status": status, "inventory": v["inventory"],
            "route_coords": v["full_path"]
        })
        
def ai_risk_analyzer(vessel):
    """
    Basit bir Anomali Tespit simülasyonu. 
    Gerçekte burada bir Isolation Forest veya LSTM modeli çalışır.
    """
    
    if vessel["speed"] > 26 or vessel["speed"] < 12:
        return "danger"
    
    
    if random.random() > 0.97: 
        return "weather_risk" 
        
    return "active"
    return {"vessels": active, "ports": PORTS, "time": time.strftime("%H:%M:%S")}

@app.get("/telemetry")
async def get_rest(): return compute_telemetry()

@app.get("/export-csv")
async def export_csv():
    data = compute_telemetry()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["IMO ID", "Gemi Adı", "Şirket", "Hedef", "Hız (knot)", "Kapasite (TEU)", "Durum", "Enlem", "Boylam"])
    
    for v in data["vessels"]:
        writer.writerow([v["id"], v["name"], v["company"], v["dest"], v["speed"], v["teu"], v["status"], v["lat"], v["lon"]])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=OrbitTrack_Report_{int(time.time())}.csv"}
    )

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_text(json.dumps(compute_telemetry()))
            await asyncio.sleep(1)
    except WebSocketDisconnect: pass

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
