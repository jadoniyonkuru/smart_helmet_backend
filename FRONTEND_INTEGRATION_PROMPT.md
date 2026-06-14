# SafeHelm Frontend — Backend Integration Prompt

> Give this entire document to the AI agent working on the frontend.
> Backend is fully running at http://localhost:8000
> All changes below must follow the existing UI_DOCUMENTATION.md conventions exactly.

---

## Context

The backend has been fully implemented and tested with real ESP32 hardware.
The frontend needs to be updated to consume real backend data instead of mock data,
and to display the new AI prediction fields that come from the 4-model inference pipeline.

Backend base URL: `http://localhost:8000/api/v1`
WebSocket base URL: `ws://localhost:8000/ws`
API docs: `http://localhost:8000/docs`

---

## Change 1 — Update `src/lib/types.ts`

Add AI fields to the `Helmet` interface and add a new `AIResult` type:

```typescript
// Update existing Helmet interface — add these fields:
interface Helmet {
  // ... keep all existing fields ...
  step_count?: number;
  heading_deg?: number;
  est_zone?: string;
  ai_prediction?: 'safe' | 'danger' | 'unknown';
  ai_confidence?: number;
  ai_danger_votes?: number;
  ai_model_votes?: {
    isolation_forest?: string;
    random_forest?: string;
    lstm?: string;
    svm?: string;
  };
}

// Add new type:
export interface AIResult {
  prediction: 'safe' | 'danger' | 'unknown';
  confidence: number;
  danger_votes: number;
  model_votes: {
    isolation_forest: string;
    random_forest: string;
    lstm: string;
    svm: string;
  };
}
```

---

## Change 2 — Update `src/lib/helmets/index.ts`

The backend helmet reading endpoint and sensor data endpoint return these field names.
Make sure the API functions map correctly:

```typescript
// POST /helmets/{id}/readings  — payload field names (camelCase from serial bridge):
// co, ch4, temperature, humidity, helmetWear, impactDetected,
// battery, signalStrength, accelerometerX/Y/Z, gasLevel,
// gyroX, gyroY, gyroZ, irValue, stepCount, headingDeg, estZone

// GET /helmets/{id}/sensor-data — response field names (snake_case from DB):
// temperature, humidity, gas_level, co_ppm, ch4_percent,
// vibration_detected, helmet_worn, accelerometer_x/y/z,
// battery_level, signal_strength, gyro_x/y/z, ir_value,
// step_count, heading_deg, est_zone,
// ai_prediction, ai_confidence, ai_danger_votes,
// ai_if_vote, ai_rf_vote, ai_lstm_vote, ai_svm_vote
```

The `useHelmetsWithReadings` hook should merge helmet data with latest sensor reading
so each helmet object includes `co_ppm`, `temperature`, `ai_prediction`, etc.

---

## Change 3 — Add AI Badge to `src/components/helmet-card.tsx`

Add an AI prediction badge to each helmet card. Place it below the status badge.

```tsx
// AI prediction badge — add to HelmetCard component
{helmet.ai_prediction && (
  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
    helmet.ai_prediction === 'danger'
      ? 'bg-critical/10 text-critical'
      : helmet.ai_prediction === 'safe'
      ? 'bg-success/10 text-success'
      : 'bg-foreground-tertiary/10 text-foreground-tertiary'
  }`}>
    AI: {helmet.ai_prediction === 'danger'
      ? `DANGER (${helmet.ai_danger_votes}/4)`
      : helmet.ai_prediction === 'safe'
      ? `Safe ${helmet.ai_confidence ? `(${helmet.ai_confidence}%)` : ''}`
      : 'Loading...'}
  </span>
)}
```

---

## Change 4 — Update Helmet Detail / View Drawer

In `src/app/dashboard/helmets/page.tsx`, update `ViewWorkerDrawer` (or equivalent helmet view drawer)
to show AI inference results as a dedicated section:

```tsx
{/* AI Inference Results section — add after sensor readings */}
<div className="space-y-3">
  <h3 className="text-sm font-semibold text-foreground-secondary uppercase tracking-wide">
    AI Safety Prediction
  </h3>

  {/* Overall prediction */}
  <div className={`rounded-lg p-4 border ${
    reading?.ai_prediction === 'danger'
      ? 'bg-critical/5 border-critical/20'
      : reading?.ai_prediction === 'safe'
      ? 'bg-success/5 border-success/20'
      : 'bg-background-tertiary border-border'
  }`}>
    <div className="flex items-center justify-between">
      <span className="text-sm font-medium text-foreground">Overall Prediction</span>
      <span className={`text-sm font-bold ${
        reading?.ai_prediction === 'danger' ? 'text-critical' :
        reading?.ai_prediction === 'safe' ? 'text-success' : 'text-foreground-tertiary'
      }`}>
        {reading?.ai_prediction?.toUpperCase() ?? 'UNKNOWN'}
      </span>
    </div>
    <div className="flex items-center justify-between mt-2">
      <span className="text-xs text-foreground-tertiary">Confidence</span>
      <span className="text-xs text-foreground">{reading?.ai_confidence ?? 0}%</span>
    </div>
    <div className="flex items-center justify-between mt-1">
      <span className="text-xs text-foreground-tertiary">Danger Votes</span>
      <span className="text-xs text-foreground">{reading?.ai_danger_votes ?? 0} / 4 models</span>
    </div>
  </div>

  {/* Per-model votes */}
  {reading?.ai_model_votes && (
    <div className="grid grid-cols-2 gap-2">
      {Object.entries({
        'Isolation Forest': reading.ai_model_votes.isolation_forest,
        'Random Forest':    reading.ai_model_votes.random_forest,
        'LSTM':             reading.ai_model_votes.lstm,
        'SVM':              reading.ai_model_votes.svm,
      }).map(([model, vote]) => (
        <div key={model} className="bg-background rounded-lg p-3 border border-border">
          <p className="text-xs text-foreground-tertiary">{model}</p>
          <p className={`text-sm font-semibold mt-1 ${
            vote === 'danger' ? 'text-critical' :
            vote === 'safe'   ? 'text-success'  : 'text-foreground-tertiary'
          }`}>
            {vote?.toUpperCase() ?? '—'}
          </p>
        </div>
      ))}
    </div>
  )}
</div>
```

---

## Change 5 — Update WebSocket Hook `src/lib/ws/index.ts`

The backend WebSocket for helmets pushes this payload on every reading:

```json
{
  "helmet_id": "uuid",
  "co_ppm": 18.4,
  "ch4_percent": 0.37,
  "temperature": 27.6,
  "humidity": 60.0,
  "helmet_worn": true,
  "vibration_detected": false,
  "battery_level": 85,
  "signal_strength": -50,
  "accelerometer_x": 10.08,
  "accelerometer_y": -0.45,
  "accelerometer_z": 1.64,
  "step_count": 17,
  "heading_deg": 194.9,
  "est_zone": "Surface Demo",
  "ai_prediction": "safe",
  "ai_confidence": 98.5,
  "ai_danger_votes": 0,
  "ai_model_votes": {
    "isolationForest": "safe",
    "randomForest": "safe",
    "lstm": "safe",
    "svm": "safe"
  },
  "recorded_at": "2026-06-14T19:29:18"
}
```

Update `useHelmetLive(helmetId)` to parse and return these fields including AI fields.
Map `ai_model_votes` keys from camelCase (WebSocket) to snake_case (types):

```typescript
// In useHelmetLive — map incoming WS message to SensorReading type:
const reading: SensorReading = {
  temperature:       msg.temperature,
  humidity:          msg.humidity,
  co_ppm:            msg.co_ppm,
  ch4_percent:       msg.ch4_percent,
  vibration_detected: msg.vibration_detected,
  helmet_worn:       msg.helmet_worn,
  battery_level:     msg.battery_level,
  signal_strength:   msg.signal_strength,
  accelerometer_x:   msg.accelerometer_x,
  accelerometer_y:   msg.accelerometer_y,
  accelerometer_z:   msg.accelerometer_z,
  step_count:        msg.step_count,
  heading_deg:       msg.heading_deg,
  est_zone:          msg.est_zone,
  ai_prediction:     msg.ai_prediction,
  ai_confidence:     msg.ai_confidence,
  ai_danger_votes:   msg.ai_danger_votes,
  ai_model_votes: {
    isolation_forest: msg.ai_model_votes?.isolationForest,
    random_forest:    msg.ai_model_votes?.randomForest,
    lstm:             msg.ai_model_votes?.lstm,
    svm:              msg.ai_model_votes?.svm,
  },
  recorded_at: msg.recorded_at,
};
```

---

## Change 6 — Update Alert Feed to Show AI Alert Type

In `src/components/alert-feed.tsx` and anywhere alerts are rendered,
add support for the `ai_danger` alert type (currently the backend uses `multi` type for AI alerts):

```tsx
// Alert type icon/color mapping — add 'multi' and 'ai_danger':
const alertTypeConfig = {
  gas:         { color: 'text-warning',  label: 'Gas Alert' },
  temperature: { color: 'text-critical', label: 'Temp Alert' },
  fall:        { color: 'text-critical', label: 'Fall Detected' },
  helmet_off:  { color: 'text-warning',  label: 'Helmet Off' },
  humidity:    { color: 'text-info',     label: 'Humidity Alert' },
  multi:       { color: 'text-critical', label: 'AI Danger Alert' },  // ← add this
};
```

---

## Change 7 — Supervisor Dashboard Home (`/dashboard`)

Update the dashboard home page to show AI-related stats.
Add a 5th card (or replace "Avg CO Level") with AI danger detections:

```tsx
// Add to stats row:
{
  label: 'AI Danger Detections',
  value: aiDangerCount,  // count alerts where type === 'multi'
  subtitle: 'Last 24 hours',
  color: 'critical',
  icon: ShieldAlert,
}
```

---

## Change 8 — Real-time Helmet Monitoring Page (`/dashboard/helmets`)

Update the helmets table to show real sensor data from the backend.
The `useHelmetsWithReadings` hook should:

1. Fetch all helmets from `GET /api/v1/helmets`
2. For each helmet with a UUID, fetch latest sensor reading from `GET /api/v1/helmets/{id}/sensor-data?limit=1`
3. Merge both into a combined object

Alternatively, use the WebSocket `useHelmetLive(id)` per helmet for live updates.

Table columns to show (updated):
| Column | Source field |
|---|---|
| Worker | `helmet.worker_name` |
| Status | `helmet.status` → badge |
| CO / CH4 | `reading.co_ppm` / `reading.ch4_percent` |
| Temp / Humidity | `reading.temperature` / `reading.humidity` |
| Helmet Wear | `reading.helmet_worn` → icon |
| AI Prediction | `reading.ai_prediction` → colored badge |
| Battery | `reading.battery_level` |
| Zone | `reading.est_zone` |
| Actions | View, Edit, Delete |

---

## Change 9 — Backend Field Name Mapping Reference

When consuming backend API responses, note these field name differences:

| What UI calls it | Backend REST field | Backend WebSocket field |
|---|---|---|
| `co` | `co_ppm` | `co_ppm` |
| `ch4` | `ch4_percent` | `ch4_percent` |
| `helmetWear` | `helmet_worn` | `helmet_worn` |
| `impactDetected` | `vibration_detected` | `vibration_detected` |
| `battery` | `battery_level` | `battery_level` |
| `signal` | `signal_strength` | `signal_strength` |
| `aiPrediction` | `ai_prediction` | `ai_prediction` |
| `aiConfidence` | `ai_confidence` | `ai_confidence` |
| `aiDangerVotes` | `ai_danger_votes` | `ai_danger_votes` |

---

## Change 10 — Environment Variables

Ensure `src/.env.local` has:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

---

## Backend Endpoints Quick Reference

All endpoints require `Authorization: Bearer <token>` header.
Token obtained from: `POST /api/v1/auth/login`

### Key endpoints for the frontend:

| Method | URL | Returns |
|---|---|---|
| POST | `/auth/login` | `{ access_token, token_type }` |
| GET | `/auth/me` | User profile |
| GET | `/helmets` | `Helmet[]` |
| POST | `/helmets` | Created helmet |
| GET | `/helmets/{id}/sensor-data?limit=1` | Latest `SensorData[]` |
| POST | `/helmets/{id}/readings` | Ingest ESP32 data |
| GET | `/workers` | `Worker[]` |
| GET | `/supervisors` | `Supervisor[]` |
| GET | `/gateways` | `Gateway[]` |
| GET | `/alerts/feed` | Latest 20 alerts |
| GET | `/alerts/unresolved` | Unresolved alerts |
| PATCH | `/alerts/{id}/resolve` | Resolve alert |
| GET | `/analytics/summary` | `{ total_helmets, total_workers, unresolved_alerts }` |
| GET | `/analytics/gas-levels` | CO/CH4 stats + distribution |
| GET | `/analytics/compliance` | `{ compliance_rate_pct, helmet_worn, total_readings }` |
| GET | `/analytics/environment` | Temperature/humidity stats |
| GET | `/analytics/impacts` | `{ total_vibration_events, fall_alerts }` |
| GET | `/analytics/alert-trends?days=7` | `[{ date, count }]` |
| GET | `/analytics/alerts-by-type` | `[{ type, count }]` |
| GET | `/analytics/alerts-by-level` | `[{ level, count }]` |
| GET | `/analytics/network-health` | Gateway online/offline stats |
| GET | `/notifications` | User notifications |
| GET | `/notifications/unread-count` | `{ count }` |
| PATCH | `/notifications/read-all` | Mark all read |

### WebSocket endpoints:
| URL | Pushes every |
|---|---|
| `ws://localhost:8000/ws/helmets/{id}` | 5 seconds — sensor data + AI results |
| `ws://localhost:8000/ws/alerts` | 5 seconds — unresolved alerts |
| `ws://localhost:8000/ws/gateways` | 10 seconds — gateway statuses |

---

## Notes for the AI Agent

1. Follow `UI_DOCUMENTATION.md` conventions exactly for all new components
2. Do not change any existing page layouts — only update data sources and add AI fields
3. All hooks must be called before any conditional returns (React rules)
4. Map snake_case backend fields to the existing camelCase frontend types
5. The backend is already running — no mock data needed for these endpoints
6. The `helmet_code` field in the backend corresponds to the numeric ID from the ESP32 firmware
7. Helmet UUIDs are used in all API calls, not the numeric helmet_code
8. The admin seeded by default: email=`admin@smarthelmet.com`, password=`admin123`
