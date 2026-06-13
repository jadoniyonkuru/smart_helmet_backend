# Smart_Helmet Backend — Complete Reference

## Overview
This document describes every backend endpoint, request/response schemas, models, services, websockets, and notable business logic implemented in the repository.

## Project entry
- FastAPI application: `app/main.py`
- API base: `/api/v1`
- WebSocket base: `/ws`
- Static uploads served at `/uploads` (avatars saved to `uploads/avatars`).

## Authentication
All protected endpoints require a Bearer JWT token. Token creation/verification and password hashing:
- `app/core/security.py`: `create_access_token`, `decode_token`, `hash_password`, `verify_password`.
- `app/core/dependencies.py`: `get_current_user`, `get_current_active_user` used as dependencies to protect routes.

## Models (database)
Key SQLAlchemy models (folder `app/models/`):
- `User` — roles: `admin`, `supervisor`, `worker` (`app/models/user.py`).
- `Helmet` — helmet metadata and status (`app/models/helmet.py`).
- `SensorData` — sensor readings (temperature, humidity, gas, CO ppm, CH4 %, vibration, accelerometer, battery, RSSI) (`app/models/sensor_data.py`).
- `Alert` — alert records with level & type (`app/models/alert.py`).
- `Gateway` — network gateway metadata (`app/models/gateway.py`).
- `Worker` — worker record, links to `User` and `Supervisor` (`app/models/worker.py`).
- `Supervisor` — supervisor record (`app/models/supervisor.py`).
- `Notification` — user notifications (`app/models/notification.py`).
- `SystemHealthLog` — periodic host health metrics (`app/models/system_health.py`).

## Pydantic Schemas
Folder `app/schemas/` maps model attributes to request/response shapes. Examples:
- `auth.py`: `LoginRequest`, `TokenResponse`, `UserCreate`, `UserResponse`, reset/change password requests.
- `helmet.py`: `HelmetCreate`, `HelmetUpdate`, `HelmetResponse`.
- `sensor_data.py`: `SensorDataResponse`, `HelmetReadingCreate`.
- `alert.py`: `AlertCreate`, `AlertResolve`, `AlertResponse`.
- `gateway.py`, `worker.py`, `supervisor.py`, `notification.py`.

## Services
Folder `app/services/` contains business logic helpers:
- `auth_service.py`: user registration, authentication (returns JWT), forgot/reset password flow (stores `reset_token` on `User` and uses `email_service`).
- `email_service.py`: sends password reset emails using `fastapi_mail`.
- `helmet_service.py`: CRUD helpers `get_all_helmets`, `get_helmet`, `create_helmet`, `update_helmet`, `delete_helmet`.
- `alert_service.py`: listing, creating, resolving alerts.
- `mqtt_service.py`: `MQTTService` wrapper around `paho.mqtt.client` for subscribe/publish; exported instance `mqtt_service`.

## API Endpoints (grouped)
All endpoints shown with method, path, required auth, and the main request/response shapes.

**Auth** (`/api/v1/auth`) — `app/api/routes/auth.py`
- POST `/register` — register user. Body: `UserCreate`. Response: `UserResponse`. No auth.
- POST `/login` — obtain JWT. Body: `LoginRequest`. Response: `TokenResponse`.
- POST `/logout` — requires auth; simple success message.
- POST `/forgot-password` — Body: `ForgotPasswordRequest` (email). Sends reset email if user exists.
- POST `/reset-password` — Body: `ResetPasswordRequest` (token + new password). Applies reset.
- GET `/me` — returns `UserResponse` for current authenticated user.
- POST `/change-password` — Body: `ChangePasswordRequest` (current & new password). Requires auth.
- PATCH `/me` — Body: `UpdateMeRequest`. Update profile fields (email uniqueness enforced).
- POST `/avatar` and POST `/me/avatar` — upload image file; saves under `uploads/avatars` and updates `User.avatar_url`.

**Helmets** (`/api/v1/helmets`) — `app/api/routes/helmets.py`
- GET `/` — list helmets. Response: `List[HelmetResponse]`.
- POST `/` — create helmet. Body: `HelmetCreate`. Response: `HelmetResponse`.
- GET `/{helmet_id}` — read helmet.
- PATCH `/{helmet_id}` — update helmet. Body: `HelmetUpdate`.
- DELETE `/{helmet_id}` — delete.
- GET `/{helmet_id}/sensor-data` — recent readings for helmet. Response: `List[SensorDataResponse]`.
- POST `/{helmet_id}/readings` — ingest sensor reading. Body: `HelmetReadingCreate` (fields: `co`, `ch4`, `temperature`, `humidity`, `helmetWear`, `impactDetected`, `battery`, `signalStrength`, `accelerometerX/Y/Z`, `gasLevel`).
  - Behavior: creates `SensorData`, updates `Helmet.last_seen`, updates `Helmet.status` to `active/warning/critical` depending on thresholds, and auto-creates `Alert` records for gas thresholds or critical events.

**Workers** (`/api/v1/workers`) — `app/api/routes/workers.py`
- GET `/` — list workers. Response: `List[WorkerResponse]`.
- POST `/` — create worker. Body: `WorkerCreate`.
- GET `/{worker_id}` — get worker.
- PATCH `/{worker_id}` — update.
- DELETE `/{worker_id}` — delete.
- GET `/{worker_id}/helmets` — helmets assigned to worker.

**Supervisors** (`/api/v1/supervisors`) — `app/api/routes/supervisors.py`
- GET `/`, POST `/`, GET `/{id}`, PATCH `/{id}`, DELETE `/{id}` — CRUD.
- GET `/{id}/workers` — workers for supervisor.
- GET `/{id}/gateways` — gateways assigned (via `supervisor_gateways` junction table).

**Gateways** (`/api/v1/gateways`) — `app/api/routes/gateways.py`
- GET `/`, POST `/`, GET `/{id}`, PATCH `/{id}`, DELETE `/{id}` — CRUD.
- GET `/{id}/status` — returns gateway metadata, `packet_delivery_rate`, `last_seen`, and connected helmet count.
- GET `/{id}/helmets` — helmets connected to gateway.

**Alerts** (`/api/v1/alerts`) — `app/api/routes/alerts.py`
- GET `/` — list alerts (supports skip/limit).
- GET `/unresolved` — unresolved alerts.
- GET `/feed` — latest 20 alerts.
- POST `/` — create alert. Body: `AlertCreate`.
- PATCH `/{alert_id}/resolve` — resolve alert. Body: `AlertResolve` (who resolved).
- DELETE `/{alert_id}` — delete.

**Analytics** (`/api/v1/analytics`) — `app/api/routes/analytics.py`
- GET `/summary` — counts for helmets, active workers, unresolved alerts.
- GET `/alert-trends` — alerts per day over N days.
- GET `/alerts-by-type`, `/alerts-by-level` — breakdowns.
- GET `/gas-levels` — averages and distribution counts for CO & CH4 using thresholds.
- GET `/compliance` — helmet-worn compliance percentage.
- GET `/impacts` — vibration events & fall alert counts.
- GET `/environment` — temperature/humidity stats.
- GET `/network-health` — gateway online/offline and avg packet delivery rate.
- GET `/active-sessions`, `/usage-trends`, `/department-distribution`, `/system-health-trends`, `/peak-hours` — various trend and distribution endpoints.

**Reports** (`/api/v1/reports`) — `app/api/routes/reports.py`
- GET `/alerts` — alerts in a date range.
- GET `/sensor-data/{helmet_id}` — sensor data in a date range for a helmet.
- POST `/generate` — generate a report (alerts + optional sensor summary). Body: `ReportRequest`.
- GET `/export` — export `alerts` or `sensor_data` as JSON or CSV (streaming CSV supported).
- GET `/audit-logs` — audit-like view built from alerts.

**Notifications** (`/api/v1/notifications`) — `app/api/routes/notifications.py`
- GET `/` — list notifications for current user (option: `unread_only`).
- GET `/unread-count` — unread count for current user.
- PATCH `/read-all` — mark all as read.
- PATCH `/{notification_id}/read` — mark one as read.

**System** (`/api/v1/system`) — `app/api/routes/system.py`
- GET `/health` — basic up check (public).
- GET `/db-health` — runs `SELECT 1` to test DB connection (public).
- GET `/performance` — records CPU/memory/disk to `SystemHealthLog` and returns current metrics (auth required).
- GET `/settings` — returns runtime settings.
- PUT `/settings` — update runtime settings (restricted keys only).

**WebSockets** (`/ws`) — `app/api/routes/ws.py` and `app/websockets/manager.py`
- `ConnectionManager` supports rooms and broadcasting.
- WS `/helmets/{helmet_id}` — pushes latest sensor data for a helmet every ~5s.
- WS `/alerts` — pushes unresolved alerts every ~5s.
- WS `/gateways` — pushes gateways and statuses every ~10s.

## Notable business logic & thresholds
- CO thresholds used in `helmets` readings ingestion:
  - CO >= 200 ppm → create CRITICAL gas alert and set helmet status to `critical`.
  - CO >= 50 ppm and <200 → create WARNING gas alert and set helmet status to `warning` if not critical.
- CH4 thresholds similarly: >=2.0% critical, >=1.0% warning.
- Vibration/fall detection and helmet worn (FSR) create alerts.
- Password reset tokens are time-limited by frontend link expectation; tokens stored on `User.reset_token`.

## Where to find code
- Routers: `app/api/routes/` (files map directly to route groups).
- Models: `app/models/`.
- Schemas: `app/schemas/`.
- Services: `app/services/`.
- Core helpers: `app/core/` (`security.py`, `dependencies.py`, `config.py`).

## Running locally (notes)
- App uses async SQLAlchemy; DB configuration is in `app/core/config.py`.
- Start with a virtualenv and dependencies from `requirements.txt`.

Example commands (PowerShell):

```powershell
# activate venv (example path used by project)
& venv\Scripts\Activate.ps1
# run uvicorn
uvicorn app.main:app --reload --port 8000
```

API docs available once running at `/docs` and `/redoc`.

---

If you want, I can next:
- generate an OpenAPI/CSV mapping of every path and schema, or
- produce a compact `API_REFERENCE.md` with one-line summaries per endpoint for copy-paste into frontend docs.


