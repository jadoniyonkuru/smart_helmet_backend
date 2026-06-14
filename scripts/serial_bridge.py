"""
serial_bridge.py — ESP32 USB Serial → FastAPI Backend Bridge
Run this on the PC connected to the ESP32 via USB.
"""

import os
import serial
import requests
import json
import time

# ── Configuration ──────────────────────────────────────────
# ── Configuration (can be overridden via environment) ─────
SERIAL_PORT = os.getenv("SERIAL_PORT", "COM5")
BAUD_RATE = int(os.getenv("BAUD_RATE", "115200"))
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
LOGIN_EMAIL = os.getenv("LOGIN_EMAIL", os.getenv("FIRST_ADMIN_EMAIL", "admin@smarthelmet.com"))
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", os.getenv("FIRST_ADMIN_PASSWORD", "admin123"))


def authenticate():
    try:
        r = requests.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        )
        if r.status_code == 200:
            token = r.json().get("access_token")
            print(f"  [AUTH] Authenticated successfully")
            return token
        else:
            print(f"  [AUTH] Login failed: {r.status_code} {r.text}")
            return None
    except Exception as e:
        print(f"  [AUTH] Error: {e}")
        return None


def load_helmet_map(headers: dict) -> dict:
    """Query backend for existing helmets and build a map helmet_code -> id"""
    try:
        r = requests.get(f"{API_BASE}/api/v1/helmets", headers=headers, timeout=5)
        if r.status_code == 200:
            items = r.json()
            return {h.get('helmet_code'): h.get('id') for h in items}
    except Exception:
        pass
    return {}


def parse_text_line(line: str) -> dict:
    """
    Parse plain-text firmware lines like:
    'Vib:NO IR:262143 Steps:26'
    into a dict compatible with transform_to_backend.
    """
    data = {}
    parts = line.split()
    for part in parts:
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        key = key.strip().upper()
        val = val.strip()
        if key == "VIB":      data["vibration"]     = val.upper() == "YES"
        elif key == "IR":     data["ir_value"]       = int(val) if val.isdigit() else 0
        elif key == "STEPS":  data["step_count"]     = int(val) if val.isdigit() else 0
        elif key == "CO":     data["co_ppm"]         = float(val)
        elif key == "CH4":    data["ch4_pct"]        = float(val)
        elif key == "TEMP":   data["temperature_c"]  = float(val)
        elif key == "HUM":    data["humidity_pct"]   = float(val)
        elif key == "AX":     data["accel_x"]        = float(val)
        elif key == "AY":     data["accel_y"]        = float(val)
        elif key == "AZ":     data["accel_z"]        = float(val)
        elif key == "GX":     data["gyro_x"]         = float(val)
        elif key == "GY":     data["gyro_y"]         = float(val)
        elif key == "GZ":     data["gyro_z"]         = float(val)
        elif key == "WORN":   data["helmet_worn"]    = val.upper() == "YES"
        elif key == "HEADING":data["heading_deg"]    = float(val)
        elif key == "RSSI":   data["rssi"]           = int(val)
        elif key == "ZONE":   data["est_zone"]       = val
    data.setdefault("helmet_id", 1)
    return data


def transform_to_backend(fw: dict) -> dict:
    return {
        "co": fw.get("co_ppm", 0),
        "ch4": fw.get("ch4_pct", 0),
        "gasLevel": int(fw.get("co_ppm", 0) or 0),
        "temperature": fw.get("temperature_c", 0),
        "humidity": fw.get("humidity_pct", 0),
        "helmetWear": fw.get("helmet_worn", True),
        "impactDetected": fw.get("vibration", False),
        "accelerometerX": fw.get("accel_x", 0),
        "accelerometerY": fw.get("accel_y", 0),
        "accelerometerZ": fw.get("accel_z", 0),
        "battery": 85.0,
        "signalStrength": fw.get("rssi", -50),
        "gyroX": fw.get("gyro_x", 0),
        "gyroY": fw.get("gyro_y", 0),
        "gyroZ": fw.get("gyro_z", 0),
        "irValue": fw.get("ir_value", 0),
        "stepCount": fw.get("step_count", 0),
        "headingDeg": fw.get("heading_deg", 0),
        "estZone": fw.get("est_zone", "Unknown"),
    }


def main():
    print("SafeHelm — Serial Bridge")
    token = authenticate()
    if not token:
        print("Cannot authenticate. Exiting.")
        return
    headers = {"Authorization": f"Bearer {token}"}
    helmet_map = load_helmet_map(headers)
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"  [SERIAL] Connected to {SERIAL_PORT}")
    except Exception as e:
        print(f"  [SERIAL] Error: {e}")
        return

    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line or not line.startswith("{"):
                continue
            try:
                fw_data = json.loads(line)
                fw_hid = fw_data.get("helmet_id", 1)
                # map firmware numeric code to UUID; fallback to env var or first helmet
                helmet_id = (
                    helmet_map.get(str(fw_hid))
                    or helmet_map.get(fw_hid)
                    or os.getenv("HELMET_UUID")
                    or (next(iter(helmet_map.values()), None))
                    or fw_hid
                )
                payload = transform_to_backend(fw_data)
                r = requests.post(
                    f"{API_BASE}/api/v1/helmets/{helmet_id}/readings",
                    json=payload,
                    headers=headers,
                    timeout=15,
                )
                if r.status_code == 201 or r.status_code == 200:
                    co = fw_data.get("co_ppm", 0)
                    temp = fw_data.get("temperature_c", 0)
                    helmet = "ON" if fw_data.get("helmet_worn") else "OFF"
                    print(f"OK | CO:{co:>5.1f} T:{temp:>4.1f} Helmet:{helmet}")
                elif r.status_code == 401:
                    print("  [AUTH] Token expired, re-authenticating...")
                    token = authenticate()
                    if token:
                        headers = {"Authorization": f"Bearer {token}"}
                        helmet_map = load_helmet_map(headers)
                else:
                    print(f"  [ERR] HTTP {r.status_code}: {r.text[:200]}")
            except json.JSONDecodeError:
                pass
            except requests.ConnectionError:
                print("  [ERR] Backend unreachable")
            except requests.Timeout:
                print("  [WARN] Request timed out — backend busy, skipping packet")
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
