"""
register_devices.py — Register real ESP32 helmets and gateways into the database.

Run once before connecting the hardware:
    python -m scripts.register_devices

This will print the helmet UUIDs you need for the serial bridge.
"""
import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.gateway import Gateway
from app.models.helmet import Helmet, HelmetStatus
from app.models.supervisor import Supervisor
from app.models.user import User, UserRole
from app.models.worker import Worker

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── CONFIGURE YOUR REAL DEVICES HERE ─────────────────────────────────────────

REAL_GATEWAYS = [
    {
        "name": "Gateway USB Demo",
        "location": "Lab / Demo Area",
        "ip_address": "USB",          # No IP in USB demo mode
        "is_online": True,
        "packet_delivery_rate": 100.0,
    },
    # Add more gateways here when LoRa gateways are deployed:
    # {
    #     "name": "Gateway Site A",
    #     "location": "Mining Level 1",
    #     "ip_address": "192.168.1.10",
    #     "is_online": True,
    #     "packet_delivery_rate": 98.5,
    # },
]

REAL_HELMETS = [
    {
        "helmet_code": "1",           # Must match helmet_id in ESP32 firmware
        "zone": "Surface Demo",
        "firmware_version": "v2.0",
        "gateway_name": "Gateway USB Demo",  # Must match a gateway name above
    },
    # Add more helmets here as you flash more ESP32 boards:
    # {
    #     "helmet_code": "2",
    #     "zone": "Tunnel A",
    #     "firmware_version": "v2.0",
    #     "gateway_name": "Gateway USB Demo",
    # },
]

REAL_WORKERS = [
    {
        "full_name": "Test Worker 1",
        "employee_id": "REAL-WRK-001",
        "phone": "+250780000001",
        "zone": "Surface Demo",
        "email": "worker1@smarthelmet.com",
        "password": "worker123",
        "helmet_code": "1",           # Assign to helmet above
    },
    # Add more workers here:
    # {
    #     "full_name": "Test Worker 2",
    #     "employee_id": "REAL-WRK-002",
    #     "phone": "+250780000002",
    #     "zone": "Tunnel A",
    #     "email": "worker2@smarthelmet.com",
    #     "password": "worker123",
    #     "helmet_code": "2",
    # },
]

# ─────────────────────────────────────────────────────────────────────────────


async def get_or_create(db: AsyncSession, model, filter_col, filter_val, **kwargs):
    result = await db.execute(select(model).where(filter_col == filter_val))
    obj = result.scalar_one_or_none()
    if obj:
        return obj, False
    obj = model(**{filter_col.key: filter_val}, **kwargs)
    db.add(obj)
    await db.flush()
    return obj, True


async def main():
    print("=" * 55)
    print("  SafeHelm — Real Device Registration")
    print("=" * 55)

    async with AsyncSessionLocal() as db:
        try:
            # ── 1. Create gateways ────────────────────────────────
            print("\n[1] Registering gateways...")
            gateway_map = {}
            for gw_data in REAL_GATEWAYS:
                gw, created = await get_or_create(
                    db, Gateway, Gateway.name, gw_data["name"],
                    location=gw_data["location"],
                    ip_address=gw_data["ip_address"],
                    is_online=gw_data["is_online"],
                    packet_delivery_rate=gw_data["packet_delivery_rate"],
                    last_seen=datetime.utcnow() if gw_data["is_online"] else None,
                )
                gateway_map[gw_data["name"]] = gw
                status = "CREATED" if created else "EXISTS"
                print(f"  [{status}] {gw.name} → {gw.id}")

            # ── 2. Create workers ─────────────────────────────────
            print("\n[2] Registering workers...")
            worker_map = {}
            for w_data in REAL_WORKERS:
                # Create user account for worker
                user_result = await db.execute(
                    select(User).where(User.email == w_data["email"])
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    user = User(
                        email=w_data["email"],
                        full_name=w_data["full_name"],
                        hashed_password=hash_password(w_data["password"]),
                        role=UserRole.worker,
                        is_active=True,
                        is_verified=True,
                    )
                    db.add(user)
                    await db.flush()

                worker, created = await get_or_create(
                    db, Worker, Worker.employee_id, w_data["employee_id"],
                    full_name=w_data["full_name"],
                    phone=w_data["phone"],
                    zone=w_data["zone"],
                    is_active=True,
                    user_id=user.id,
                )
                worker_map[w_data["helmet_code"]] = worker
                status = "CREATED" if created else "EXISTS"
                print(f"  [{status}] {worker.full_name} ({worker.employee_id})")

            # ── 3. Create helmets ─────────────────────────────────
            print("\n[3] Registering helmets...")
            print("\n  ┌─────────────────────────────────────────────────────────────┐")
            print("  │  HELMET UUIDs — copy these for the serial bridge             │")
            print("  └─────────────────────────────────────────────────────────────┘")

            for h_data in REAL_HELMETS:
                gateway = gateway_map.get(h_data["gateway_name"])
                worker = worker_map.get(h_data["helmet_code"])

                helmet, created = await get_or_create(
                    db, Helmet, Helmet.helmet_code, h_data["helmet_code"],
                    zone=h_data["zone"],
                    firmware_version=h_data["firmware_version"],
                    status=HelmetStatus.inactive,
                    is_active=True,
                    gateway_id=gateway.id if gateway else None,
                    worker_id=worker.id if worker else None,
                )
                status = "CREATED" if created else "EXISTS"
                print(f"\n  [{status}] Helmet code: {helmet.helmet_code}")
                print(f"    UUID      : {helmet.id}   ← use this in serial bridge")
                print(f"    Zone      : {helmet.zone}")
                print(f"    Worker    : {worker.full_name if worker else 'Unassigned'}")
                print(f"    Gateway   : {gateway.name if gateway else 'None'}")
                print(f"    Firmware  : {helmet.firmware_version}")

            await db.commit()

            # ── 4. Print serial bridge command ────────────────────
            print("\n" + "=" * 55)
            print("  Registration complete!")
            print("=" * 55)
            print("\n  To start the serial bridge, run:")
            print("\n  $env:SERIAL_PORT=\"COM5\"  # change to your port")
            print("  $env:LOGIN_EMAIL=\"admin@smarthelmet.com\"")
            print("  $env:LOGIN_PASSWORD=\"admin123\"")
            print("  venv\\Scripts\\python.exe scripts/serial_bridge.py")
            print("\n  The bridge auto-maps helmet_code '1' → UUID above.")
            print("  Make sure the ESP32 firmware sends: \"helmet_id\": 1")

        except Exception as e:
            await db.rollback()
            print(f"\n  ERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
