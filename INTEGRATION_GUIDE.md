# SafeHelm Backend — Hardware Integration Guide

> **For:** Jean de Dieu NIYONKURU (AI Team) & Hardware Integration Partner  
> **Written by:** Jean D'Amour KUBWIMANA (IoT/Backend Team)  
> **Backend status:** ✅ Fully implemented and running

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Project Structure](#2-project-structure)
3. [Environment Setup](#3-environment-setup)
4. [Database Setup](#4-database-setup)
5. [Running the Backend](#5-running-the-backend)
6. [Connecting the ESP32 Hardware](#6-connecting-the-esp32-hardware)
7. [Serial Bridge — How It Works](#7-serial-bridge--how-it-works)
8. [API Endpoints Reference](#8-api-endpoints-reference)
9. [WebSocket Reference](#9-websocket-reference)
10. [AI Model Pipeline](#10-ai-model-pipeline)
11. [Alert Logic](#11-alert-logic)
12. [Frontend Integration](#12-frontend-integration)
13. [Hardware Reference](#13-hardware-reference)

---

## 1. Quick Start

```powershell
# 1. Clone the repo and enter the folder
cd smart_helmet_backend

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# 3. Install dependencies
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip install scikit-learn joblib numpy tensorflow tf-keras

# 4. Copy env file and fill in your values
copy .env.example .env

# 5. Run database migrations
venv\Scripts\python.exe -m alembic upgrade head

# 6. Start the server
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Server runs at: **http://localhost:8000**  
API docs at: **http://localhost:8000/docs**

---

## 2. Project Structure

```
smart_helmet_backend/
├── app/
│   ├── main.py                  # FastAPI entry point, startup, routes
│   ├── api/routes/              # All REST + WebSocket route handlers
│   │   ├── auth.py              # Login, register, password reset
│   │   ├── helmets.py           # Helmet CRUD + sensor reading ingestion ← KEY FILE
│   │   ├── workers.py           # Worker management
│   │   ├── supervisors.py       # Supervisor management
│   │   ├── gateways.py          # Gateway management
│   │   ├── alerts.py            # Alert CRUD and resolution
│   │   ├── analytics.py         # Dashboard analytics endpoints
│   │   ├── reports.py           # Report generation and export
│   │   ├── notifications.py     # User notifications
│   │   ├── system.py            # Health checks and system metrics
│   │   └── ws.py                # WebSocket endpoints
│   ├── core/
│   │   ├── config.py            # All env variables via pydantic-settings
│   │   ├── security.py          # JWT creation, password hashing
│   │   └── dependencies.py      # Auth dependency injection
│   ├── db/
│   │   ├── base.py              # SQLAlchemy declarative base
│   │   └── session.py           # Async DB engine and session
│   ├── models/                  # SQLAlchemy table definitions
│   ├── schemas/                 # Pydantic request/response models
│   ├── services/
│   │   ├── ai_service.py        # 4-model AI inference pipeline ← KEY FILE
│   │   ├── auth_service.py      # Auth business logic
│   │   ├── helmet_service.py    # Helmet CRUD logic
│   │   ├── alert_service.py     # Alert logic
│   │   ├── email_service.py     # Email (password reset)
│   │   └── mqtt_service.py      # MQTT subscriber/publisher
│   └── websockets/
│       └── manager.py           # WebSocket room manager
├── scripts/
│   └── serial_bridge.py         # ESP32 USB → Backend bridge ← RUN THIS
├── smart-helmet-ai-models/      # Trained ML model files
│   ├── model1_isolation_forest.pkl
│   ├── model2_random_forest.pkl
│   ├── model3_lstm.h5
│   ├── model4_svm.pkl
│   ├── scaler.pkl
│   └── feature_cols.pkl
├── alembic/                     # Database migration scripts
├── .env                         # Your local environment variables (never commit)
├── .env.example                 # Template — copy this to .env
└── requirements.txt
```

---

## 3. Environment Setup

Copy `.env.example` to `.env` and update these values:

```env
# PostgreSQL — update password to match your postgres installation
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/smart_helmet_db

# Security — change this to a long random string in production
SECRET_KEY=your-super-secret-key-change-this-in-production

# Admin account auto-created on first startup
FIRST_ADMIN_EMAIL=admin@smarthelmet.com
FIRST_ADMIN_PASSWORD=admin123

# MQTT — leave blank if not using LoRa gateways yet
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
```

---

## 4. Database Setup

**Option A — pgAdmin (GUI):**
1. Open pgAdmin → right-click Databases → Create → Database
2. Name it `smart_helmet_db` → Save

**Option B — psql (terminal):**
```powershell
psql -U postgres
```
Then inside psql:
```sql
CREATE DATABASE smart_helmet_db;
\q
```

**Run migrations:**
```powershell
venv\Scripts\python.exe -m alembic upgrade head
```

This creates all tables automatically. The admin user from `.env` is seeded on first startup.

---

## 5. Running the Backend

```powershell
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Expected startup output:**
```
[AI] All 4 models loaded successfully
[STARTUP] AI models loaded — inference active
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## 6. Connecting the ESP32 Hardware

### Step 1 — Connect ESP32 via USB
Plug the ESP32 into the PC running the backend via USB cable.

### Step 2 — Find the COM port
Run in PowerShell:
```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```
You will see something like `COM3`, `COM5`. Note your port.

> **Important:** Close Arduino Serial Monitor before running the bridge — both cannot use the same COM port simultaneously.

### Step 3 — Create a helmet record in the backend
Before sending readings, the helmet must exist in the database.

**Login first** (POST `/api/v1/auth/login`):
```json
{
  "email": "admin@smarthelmet.com",
  "password": "admin123"
}
```
Copy the `access_token` from the response.

**Create a helmet** (POST `/api/v1/helmets`):
```json
{
  "helmet_code": "1",
  "name": "Helmet 01",
  "model": "SafeHelm v2.0"
}
```
Copy the `id` (UUID) from the response — you need it for the serial bridge.

### Step 4 — Run the serial bridge

```powershell
$env:SERIAL_PORT="COM5"
$env:LOGIN_EMAIL="admin@smarthelmet.com"
$env:LOGIN_PASSWORD="admin123"
venv\Scripts\python.exe scripts/serial_bridge.py
```

Replace `COM5` with your actual port.

**Expected output:**
```
SafeHelm — Serial Bridge
  [AUTH] Authenticated successfully
  [SERIAL] Connected to COM5
  [READY] Bridge running. Open dashboard to see live data.
  [   1] OK | CO:  18.4 T:27.6 Helmet:ON
  [   2] OK | CO:  19.1 T:27.7 Helmet:ON
```

---

## 7. Serial Bridge — How It Works

The bridge (`scripts/serial_bridge.py`) does the following:

```
ESP32 USB Serial (115200 baud)
        │
        │  JSON packet every 2 seconds:
        │  {"helmet_id":1,"co_ppm":18.4,"temperature_c":27.6,...}
        │
        ▼
serial_bridge.py
        │
        │  1. Reads JSON lines from COM port
        │  2. Ignores lines starting with # (debug messages)
        │  3. Maps firmware field names → backend field names
        │  4. Authenticates with JWT (auto-refreshes on 401)
        │  5. POSTs to: POST /api/v1/helmets/{helmet_id}/readings
        │
        ▼
FastAPI Backend
        │
        │  1. Stores SensorData record
        │  2. Runs 4-model AI inference
        │  3. Creates alerts if thresholds exceeded
        │  4. Pushes live data via WebSocket
        │
        ▼
React Dashboard (WebSocket)
```

### Field Mapping (firmware → backend)

| ESP32 field | Backend field | Notes |
|---|---|---|
| `co_ppm` | `co` | Carbon monoxide ppm |
| `ch4_pct` | `ch4` | Methane % |
| `temperature_c` | `temperature` | °C |
| `humidity_pct` | `humidity` | % |
| `helmet_worn` | `helmetWear` | bool |
| `vibration` | `impactDetected` | bool |
| `accel_x/y/z` | `accelerometerX/Y/Z` | m/s² |
| `gyro_x/y/z` | `gyroX/Y/Z` | °/s |
| `ir_value` | `irValue` | MAX30102 raw |
| `step_count` | `stepCount` | cumulative |
| `heading_deg` | `headingDeg` | 0-360° |
| `est_zone` | `estZone` | zone label |
| `rssi` | `signalStrength` | dBm |

---

## 8. API Endpoints Reference

Base URL: `http://localhost:8000/api/v1`  
All endpoints except `/auth/login`, `/auth/register`, `/system/health` require:  
`Authorization: Bearer <token>`

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Login → returns JWT token |
| POST | `/auth/register` | Register new user |
| GET | `/auth/me` | Get current user profile |
| POST | `/auth/forgot-password` | Send password reset email |
| POST | `/auth/reset-password` | Reset password with token |
| PATCH | `/auth/me` | Update profile |
| POST | `/auth/avatar` | Upload profile avatar |

### Helmets
| Method | Path | Description |
|---|---|---|
| GET | `/helmets` | List all helmets |
| POST | `/helmets` | Create helmet |
| GET | `/helmets/{id}` | Get helmet by ID |
| PATCH | `/helmets/{id}` | Update helmet |
| DELETE | `/helmets/{id}` | Delete helmet |
| GET | `/helmets/{id}/sensor-data` | Last N readings |
| **POST** | **`/helmets/{id}/readings`** | **Ingest sensor reading from ESP32** |

### Sensor Reading Payload (`POST /helmets/{id}/readings`)
```json
{
  "co": 18.4,
  "ch4": 0.37,
  "temperature": 27.6,
  "humidity": 60.0,
  "helmetWear": true,
  "impactDetected": false,
  "battery": 85.0,
  "signalStrength": -50,
  "accelerometerX": 10.08,
  "accelerometerY": -0.45,
  "accelerometerZ": 1.64,
  "gasLevel": 18,
  "gyroX": -3.69,
  "gyroY": -2.02,
  "gyroZ": 4.14,
  "irValue": 55377,
  "stepCount": 17,
  "headingDeg": 194.9,
  "estZone": "Surface Demo"
}
```

### Workers
| Method | Path | Description |
|---|---|---|
| GET | `/workers` | List workers |
| POST | `/workers` | Create worker |
| GET | `/workers/{id}` | Get worker |
| PATCH | `/workers/{id}` | Update worker |
| DELETE | `/workers/{id}` | Delete worker |

### Alerts
| Method | Path | Description |
|---|---|---|
| GET | `/alerts` | List all alerts |
| GET | `/alerts/unresolved` | Unresolved alerts only |
| GET | `/alerts/feed` | Latest 20 alerts |
| PATCH | `/alerts/{id}/resolve` | Resolve an alert |

### Analytics
| Method | Path | Description |
|---|---|---|
| GET | `/analytics/summary` | Totals: helmets, workers, alerts |
| GET | `/analytics/gas-levels` | CO/CH4 averages and distribution |
| GET | `/analytics/compliance` | Helmet wear compliance % |
| GET | `/analytics/environment` | Temperature/humidity stats |
| GET | `/analytics/impacts` | Vibration and fall counts |
| GET | `/analytics/alert-trends` | Alerts per day (last N days) |
| GET | `/analytics/alerts-by-type` | Breakdown by alert type |
| GET | `/analytics/alerts-by-level` | Breakdown by alert level |
| GET | `/analytics/network-health` | Gateway online status |
| GET | `/analytics/peak-hours` | Alert count by hour of day |

---

## 9. WebSocket Reference

Connect from the frontend using standard WebSocket API.

### Live Helmet Sensor Data
```
ws://localhost:8000/ws/helmets/{helmet_id}
```
Pushes every 5 seconds:
```json
{
  "helmet_id": "uuid",
  "co_ppm": 18.4,
  "temperature": 27.6,
  "humidity": 60.0,
  "helmet_worn": true,
  "vibration_detected": false,
  "step_count": 17,
  "heading_deg": 194.9,
  "est_zone": "Surface Demo",
  "ai_prediction": "safe",
  "ai_confidence": 98.5,
  "ai_danger_votes": 0,
  "ai_model_votes": {
    "isolation_forest": "safe",
    "random_forest": "safe",
    "lstm": "safe",
    "svm": "safe"
  },
  "recorded_at": "2026-06-13T14:30:00"
}
```

### Live Alerts Feed
```
ws://localhost:8000/ws/alerts
```
Pushes every 5 seconds:
```json
{
  "type": "unresolved_alerts",
  "count": 2,
  "alerts": [
    {
      "id": "uuid",
      "level": "critical",
      "type": "gas",
      "message": "Critical CO level: 210.0 ppm",
      "helmet_id": "uuid",
      "created_at": "2026-06-13T14:30:00"
    }
  ]
}
```

### Gateway Status
```
ws://localhost:8000/ws/gateways
```
Pushes every 10 seconds with all gateway statuses.

---

## 10. AI Model Pipeline

Every sensor reading triggers a 4-model majority vote inference.

### Models
| # | Model | File | Type |
|---|---|---|---|
| 1 | Isolation Forest | `model1_isolation_forest.pkl` | Anomaly detection |
| 2 | Random Forest | `model2_random_forest.pkl` | Classification + confidence |
| 3 | LSTM Neural Network | `model3_lstm.h5` | Temporal sequence (needs 10 readings to warm up) |
| 4 | SVM | `model4_svm.pkl` | Classification |

### Voting Logic
```
Votes    Result
──────────────────────────────────────────────────────
4/4      → danger (unanimous)
3/4      → danger (clear majority)
2/4 tie  → danger ONLY if RF voted danger AND RF confidence ≥ 75%
           otherwise → safe (avoids false alerts)
1/4      → safe
0/4      → safe (unanimous)
```

### Feature Vector (7 features fed to all models)
```
[co_ppm, co_ppm, ch4_pct×100, co_ppm, temperature_c, humidity_pct, co_ppm]
```
Scaled using `scaler.pkl` before inference.

### AI Result in Response
```json
{
  "ai_prediction": "safe",
  "ai_confidence": 98.5,
  "ai_danger_votes": 0,
  "ai_if_vote": "safe",
  "ai_rf_vote": "safe",
  "ai_lstm_vote": "safe",
  "ai_svm_vote": "safe"
}
```

> **Note:** LSTM returns safe (0) for the first 10 readings per helmet while its buffer fills up. This is expected behavior.

---

## 11. Alert Logic

Alerts are created automatically on every sensor reading. Three levels:

### Level 1 — Gas Thresholds
| Condition | Type | Level |
|---|---|---|
| CO ≥ 200 ppm | `gas` | `critical` |
| CO ≥ 50 ppm | `gas` | `warning` |
| CH4 ≥ 2.0% | `gas` | `critical` |
| CH4 ≥ 1.0% | `gas` | `warning` |

### Level 2 — Safety Thresholds
| Condition | Type | Level |
|---|---|---|
| Temperature > 55°C | `temperature` | `critical` |
| Temperature > 40°C | `temperature` | `warning` |
| Impact detected | `fall` | `critical` |
| Helmet not worn | `helmet_off` | `warning` |

### Level 3 — AI Danger Detection
| Condition | Type | Level |
|---|---|---|
| AI votes ≥ 3/4 danger | `multi` | `critical` |
| AI votes = 2/4 + RF confident | `multi` | `warning` |

### Helmet Status Updates
- Any `critical` alert → helmet status = `critical`
- Any `warning` alert → helmet status = `warning`
- Normal reading → helmet status = `active`

---

## 12. Frontend Integration

The React frontend connects to this backend. Key integration points:

### Authentication
```typescript
// POST /api/v1/auth/login
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
})
const { access_token } = await response.json()
// Store token and attach as: Authorization: Bearer <token>
```

### WebSocket Connection
```typescript
const ws = new WebSocket(`ws://localhost:8000/ws/helmets/${helmetId}`)
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  // data.ai_prediction → 'safe' | 'danger' | 'unknown'
  // data.co_ppm, data.temperature, etc.
}
```

### AI Badge Display
```typescript
// Suggested display logic
if (data.ai_prediction === 'danger') {
  // Red badge: "AI: DANGER (3/4 votes)"
} else if (data.ai_prediction === 'safe') {
  // Green badge: "AI: Safe (98.5%)"
} else {
  // Gray badge: "AI: Loading..." (first 10 readings)
}
```

---

## 13. Hardware Reference

### Connected Components
| Component | Model | Interface | ESP32 Pin | Status |
|---|---|---|---|---|
| Gas sensor | MQ-2 | Analog | D34 | ✅ Auto-calibrating (30s warmup) |
| Temp/Humidity | DHT11 | Digital | D15 | ✅ Working |
| IMU | MPU6050 | I2C | D21/D22 | ✅ Working |
| Helmet detect | MAX30102 | I2C | D21/D22 | ✅ IR threshold = 10000 |
| Vibration | MPU6050 (computed) | — | — | ✅ Software detection |
| Buzzer | HW-508 | Digital | D25 | ✅ Working |
| Alert LED | Red LED + 220Ω | Digital | D26 | ✅ Working |
| Status LED | Green LED + 220Ω | Digital | D27 | ✅ Working |

### ESP32 Firmware Behavior
- **Baud rate:** 115200
- **Packet interval:** every 2 seconds
- **Packet format:** JSON lines starting with `{` (lines starting with `#` are debug — ignored by bridge)
- **MQ-2 warmup:** CO and CH4 report 0 for first 30 seconds after power-on (auto-calibration). Treat as valid clean-air readings.
- **RSSI=−50, nearest_gateway_id=0:** indicates USB demo mode (no LoRa gateway connected)

### Sample ESP32 Packet
```json
{
  "helmet_id": 1,
  "timestamp": 120035,
  "co_ppm": 18.4,
  "ch4_pct": 0.37,
  "temperature_c": 27.6,
  "humidity_pct": 60.0,
  "accel_x": 10.08,
  "accel_y": -0.45,
  "accel_z": 1.64,
  "gyro_x": -3.69,
  "gyro_y": -2.02,
  "gyro_z": 4.14,
  "helmet_worn": true,
  "vibration": false,
  "ir_value": 55377,
  "step_count": 17,
  "heading_deg": 194.9,
  "nearest_gateway_id": 0,
  "rssi": -50,
  "est_zone": "Surface Demo",
  "alert_gas": false,
  "alert_temp": false,
  "alert_fall": false,
  "alert_helmet": false,
  "alert_vibration": false
}
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: fastapi` | Run `venv\Scripts\Activate.ps1` then `pip install -r requirements.txt` |
| `[AI] Error loading models` | Run `pip install scikit-learn joblib numpy tensorflow tf-keras` |
| `could not open port COM3` | Close Arduino Serial Monitor first; check correct port with `[System.IO.Ports.SerialPort]::GetPortNames()` |
| `[AUTH] Login failed` | Check `FIRST_ADMIN_EMAIL` and `FIRST_ADMIN_PASSWORD` in `.env` match what you're using |
| `alembic upgrade head` fails | Make sure PostgreSQL is running and `DATABASE_URL` in `.env` is correct |
| LSTM always returns `safe` | Expected for first 10 readings — buffer needs to fill up |
| `InconsistentVersionWarning` sklearn | Harmless — models still work despite version mismatch |

---

*Backend by Jean D'Amour KUBWIMANA — IoT Team*  
*AI Models by Jean de Dieu NIYONKURU — AI Team*
