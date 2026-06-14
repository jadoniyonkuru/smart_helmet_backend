# SafeHelm — ESP32 Firmware JSON Output Guide

> **For:** Hardware/Firmware Developer (Jean de Dieu NIYONKURU)  
> **Written by:** Jean D'Amour KUBWIMANA (Backend Team)  
> **Purpose:** Update ESP32 firmware to output JSON so the backend bridge can read sensor data

---

## The Problem

The current firmware outputs plain text like this:
```
Vib:NO IR:262143 Steps:26
```

The backend serial bridge **cannot parse this**. It only reads JSON lines like this:
```json
{"helmet_id":1,"co_ppm":18.4,"temperature_c":27.6,"humidity_pct":60.0,...}
```

**One firmware change fixes everything.**

---

## Step 1 — Install ArduinoJson Library

In Arduino IDE:
1. Go to **Sketch → Include Library → Manage Libraries**
2. Search for `ArduinoJson`
3. Install the one by **Benoit Blanchon** — version **6.x**

---

## Step 2 — Add Include at Top of Firmware

At the very top of your `.ino` file, add:

```cpp
#include <ArduinoJson.h>
```

---

## Step 3 — Replace Serial Print Section with JSON Output

Find the section in your loop() where you currently print sensor data to Serial.

It probably looks something like this (what you have now):
```cpp
// OLD — plain text output (backend cannot read this)
Serial.print("Vib:"); Serial.print(vibration ? "YES" : "NO");
Serial.print(" IR:"); Serial.print(ir_value);
Serial.println(" Steps:" + String(step_count));
```

**Delete that entire block** and replace with this:

```cpp
// NEW — JSON output (backend reads this correctly)
StaticJsonDocument<512> doc;

doc["helmet_id"]       = 1;                // ← change this number per helmet (1, 2, 3...)
doc["co_ppm"]          = co_ppm;
doc["ch4_pct"]         = ch4_pct;
doc["temperature_c"]   = temperature;
doc["humidity_pct"]    = humidity;
doc["accel_x"]         = accel_x;
doc["accel_y"]         = accel_y;
doc["accel_z"]         = accel_z;
doc["gyro_x"]          = gyro_x;
doc["gyro_y"]          = gyro_y;
doc["gyro_z"]          = gyro_z;
doc["helmet_worn"]     = helmet_worn;
doc["vibration"]       = vibration;
doc["ir_value"]        = ir_value;
doc["step_count"]      = step_count;
doc["heading_deg"]     = heading_deg;
doc["rssi"]            = -50;
doc["est_zone"]        = "Surface Demo";
doc["alert_gas"]       = alert_gas;
doc["alert_temp"]      = alert_temp;
doc["alert_fall"]      = alert_fall;
doc["alert_helmet"]    = alert_helmet;
doc["alert_vibration"] = alert_vibration;

serializeJson(doc, Serial);
Serial.println();    // ← REQUIRED: newline after every packet
```

---

## Step 4 — Change Debug Prints to Start with #

The bridge ignores any line starting with `#`.  
Change all your existing debug Serial prints to start with `#`:

```cpp
// OLD
Serial.println("Boot complete");
Serial.println("Calibrating MQ-2...");
Serial.println("DHT11 read failed");

// NEW — prefix with # so bridge ignores them
Serial.println("# Boot complete");
Serial.println("# Calibrating MQ-2...");
Serial.println("# DHT11 read failed");
```

---

## Step 5 — Variable Name Reference

Match your variable names to the JSON keys. Here is the expected mapping:

| JSON key | Your variable | Sensor | Notes |
|---|---|---|---|
| `helmet_id` | hardcoded `1` | — | Change per board: 1, 2, 3... |
| `co_ppm` | `co_ppm` | MQ-2 | Carbon monoxide ppm |
| `ch4_pct` | `ch4_pct` | MQ-2 | Methane % (0.0 to 10.0) |
| `temperature_c` | `temperature` | DHT11 | Celsius |
| `humidity_pct` | `humidity` | DHT11 | % relative humidity |
| `accel_x` | `accel_x` | MPU6050 | m/s² |
| `accel_y` | `accel_y` | MPU6050 | m/s² |
| `accel_z` | `accel_z` | MPU6050 | m/s² |
| `gyro_x` | `gyro_x` | MPU6050 | °/s |
| `gyro_y` | `gyro_y` | MPU6050 | °/s |
| `gyro_z` | `gyro_z` | MPU6050 | °/s |
| `helmet_worn` | `helmet_worn` | MAX30102 | true/false (IR > 10000) |
| `vibration` | `vibration` | MPU6050 | true/false |
| `ir_value` | `ir_value` | MAX30102 | raw int 0–262143 |
| `step_count` | `step_count` | MPU6050 | cumulative int |
| `heading_deg` | `heading_deg` | MPU6050 | 0.0–360.0 |
| `rssi` | hardcoded `-50` | — | USB demo mode value |
| `est_zone` | hardcoded `"Surface Demo"` | — | Change to actual zone |
| `alert_gas` | `alert_gas` | firmware logic | bool |
| `alert_temp` | `alert_temp` | firmware logic | bool |
| `alert_fall` | `alert_fall` | firmware logic | bool |
| `alert_helmet` | `alert_helmet` | firmware logic | bool |
| `alert_vibration` | `alert_vibration` | firmware logic | bool |

> If your variable names are different, just replace the right side.  
> Example: if your temperature variable is called `temp_c`, use `doc["temperature_c"] = temp_c;`

---

## Step 6 — Complete loop() Example

Here is what the bottom of your loop() should look like after the change:

```cpp
void loop() {
  // ... all your existing sensor reading code stays the same ...
  // ... read DHT11, MPU6050, MQ-2, MAX30102 as before ...

  // ── Alert logic (keep your existing threshold checks) ──
  alert_gas       = (co_ppm > 200 || ch4_pct > 4.0);
  alert_temp      = (temperature > 45.0);
  alert_fall      = (accel_magnitude_change > 3.0);
  alert_helmet    = !helmet_worn;
  alert_vibration = vibration;

  // ── Buzzer / LED (keep your existing code) ─────────────
  if (alert_gas || alert_fall) {
    digitalWrite(BUZZER_PIN, HIGH);
    digitalWrite(LED_RED_PIN, HIGH);
  } else {
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
  }

  // ── JSON Serial Output (REPLACE old Serial.print block) ─
  StaticJsonDocument<512> doc;
  doc["helmet_id"]       = 1;
  doc["co_ppm"]          = co_ppm;
  doc["ch4_pct"]         = ch4_pct;
  doc["temperature_c"]   = temperature;
  doc["humidity_pct"]    = humidity;
  doc["accel_x"]         = accel_x;
  doc["accel_y"]         = accel_y;
  doc["accel_z"]         = accel_z;
  doc["gyro_x"]          = gyro_x;
  doc["gyro_y"]          = gyro_y;
  doc["gyro_z"]          = gyro_z;
  doc["helmet_worn"]     = helmet_worn;
  doc["vibration"]       = vibration;
  doc["ir_value"]        = ir_value;
  doc["step_count"]      = step_count;
  doc["heading_deg"]     = heading_deg;
  doc["rssi"]            = -50;
  doc["est_zone"]        = "Surface Demo";
  doc["alert_gas"]       = alert_gas;
  doc["alert_temp"]      = alert_temp;
  doc["alert_fall"]      = alert_fall;
  doc["alert_helmet"]    = alert_helmet;
  doc["alert_vibration"] = alert_vibration;

  serializeJson(doc, Serial);
  Serial.println();

  delay(2000);   // send packet every 2 seconds
}
```

---

## Step 7 — Flash and Verify

After flashing the updated firmware:

1. Open Arduino Serial Monitor at **115200 baud**
2. You should see one JSON line every 2 seconds:
```
{"helmet_id":1,"co_ppm":18.4,"ch4_pct":0.37,"temperature_c":27.6,...}
{"helmet_id":1,"co_ppm":18.5,"ch4_pct":0.36,"temperature_c":27.7,...}
```

3. **Close Arduino Serial Monitor** before running the backend bridge  
   (both cannot use COM3 at the same time)

---

## Step 8 — Verify from Backend Side

On the backend PC, run this to confirm the output looks correct:

```powershell
venv\Scripts\python.exe -c "
import serial, json
s = serial.Serial('COM3', 115200, timeout=3)
print('Reading 5 packets...')
count = 0
while count < 5:
    line = s.readline().decode('utf-8', errors='ignore').strip()
    if not line or not line.startswith('{'):
        continue
    data = json.loads(line)
    print(f'  CO:{data[\"co_ppm\"]} Temp:{data[\"temperature_c\"]} Worn:{data[\"helmet_worn\"]}')
    count += 1
s.close()
print('All good!')
"
```

Expected output:
```
Reading 5 packets...
  CO:18.4 Temp:27.6 Worn:True
  CO:19.1 Temp:27.7 Worn:True
  CO:18.8 Temp:27.6 Worn:True
  CO:18.6 Temp:27.5 Worn:True
  CO:19.0 Temp:27.8 Worn:True
All good!
```

---

## Step 9 — Run the Serial Bridge

Once output is confirmed, start the bridge:

```powershell
$env:SERIAL_PORT="COM3"
$env:LOGIN_EMAIL="admin@smarthelmet.com"
$env:LOGIN_PASSWORD="admin123"
venv\Scripts\python.exe scripts/serial_bridge.py
```

Expected output:
```
SafeHelm — Serial Bridge
  [AUTH] Authenticated successfully
  [SERIAL] Connected to COM3
  [   1] OK | CO:  18.4 T:27.6 Helmet:ON
  [   2] OK | CO:  19.1 T:27.7 Helmet:ON
```

Live data will now appear on the dashboard at **http://localhost:3000**

---

## Two Rules — Must Not Break

| Rule | Why |
|---|---|
| Every JSON packet must be on **one single line** followed by `\n` | `serializeJson()` + `Serial.println()` handles this automatically |
| Debug prints must start with `#` | Bridge skips any line not starting with `{` so `#` lines are safely ignored |

---

## Multiple Helmets

When you have more than one ESP32 board, change `helmet_id` per board:

```cpp
// Board 1
doc["helmet_id"] = 1;
doc["est_zone"]  = "Surface Demo";

// Board 2
doc["helmet_id"] = 2;
doc["est_zone"]  = "Tunnel A";

// Board 3
doc["helmet_id"] = 3;
doc["est_zone"]  = "Tunnel B";
```

Each board connects to a separate PC USB port or the same PC with multiple COM ports.  
The backend already has helmet code `"1"` registered. Run `register_devices.py` to add more helmets.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ArduinoJson.h: No such file` | Install ArduinoJson library in Arduino IDE (Step 1) |
| `StaticJsonDocument` is too small | Increase size: `StaticJsonDocument<1024> doc;` |
| Serial Monitor shows garbled text | Wrong baud rate — set to **115200** |
| Bridge still shows no data | Make sure `Serial.println()` is after `serializeJson()` |
| Bridge shows `[ERR] Backend unreachable` | Start the backend first: `uvicorn app.main:app --reload` |
| COM3 not found | Close Arduino Serial Monitor before running bridge |

---

*Firmware guide by Jean D'Amour KUBWIMANA — IoT/Backend Team*  
*For hardware questions contact the IoT team*
