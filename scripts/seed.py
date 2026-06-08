"""
Run: python -m scripts.seed
Creates supervisors, workers, gateways, helmets, sensor readings, and alerts.
Safe to re-run — skips rows that already exist by employee_id / unique keys.
"""
import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base, supervisor_gateways
from app.models.alert import Alert, AlertLevel, AlertType
from app.models.gateway import Gateway
from app.models.helmet import Helmet, HelmetStatus
from app.models.notification import Notification, NotificationType
from app.models.sensor_data import SensorData
from app.models.supervisor import Supervisor
from app.models.system_health import SystemHealthLog
from app.models.user import User, UserRole
from app.models.worker import Worker

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

ZONES = ["Zone A - Mining", "Zone B - Chemical", "Zone C - Welding", "Zone D - Construction"]

# ── helpers ──────────────────────────────────────────────────────────────────

def rand_dt(days_ago_max: int = 7) -> datetime:
    return datetime.utcnow() - timedelta(
        days=random.uniform(0, days_ago_max),
        hours=random.uniform(0, 23),
        minutes=random.uniform(0, 59),
    )


async def get_or_create_user(db: AsyncSession, email: str, full_name: str,
                              password: str, role: UserRole) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


async def get_or_create_supervisor(db: AsyncSession, employee_id: str,
                                    full_name: str, phone: str,
                                    user_id) -> Supervisor:
    result = await db.execute(select(Supervisor).where(Supervisor.employee_id == employee_id))
    sup = result.scalar_one_or_none()
    if sup:
        return sup
    sup = Supervisor(full_name=full_name, employee_id=employee_id,
                     phone=phone, is_active=True, user_id=user_id)
    db.add(sup)
    await db.flush()
    return sup


async def get_or_create_worker(db: AsyncSession, employee_id: str, full_name: str,
                                phone: str, zone: str,
                                supervisor_id, user_id) -> Worker:
    result = await db.execute(select(Worker).where(Worker.employee_id == employee_id))
    w = result.scalar_one_or_none()
    if w:
        return w
    w = Worker(full_name=full_name, employee_id=employee_id, phone=phone,
               zone=zone, is_active=True, supervisor_id=supervisor_id, user_id=user_id)
    db.add(w)
    await db.flush()
    return w


async def get_or_create_gateway(db: AsyncSession, name: str, location: str,
                                 ip_address: str, is_online: bool,
                                 pdr: float) -> Gateway:
    result = await db.execute(select(Gateway).where(Gateway.name == name))
    gw = result.scalar_one_or_none()
    if gw:
        return gw
    gw = Gateway(name=name, location=location, ip_address=ip_address,
                 is_online=is_online, last_seen=datetime.utcnow() if is_online else None,
                 packet_delivery_rate=pdr)
    db.add(gw)
    await db.flush()
    return gw


async def get_or_create_helmet(db: AsyncSession, code: str, zone: str,
                                gateway_id, worker_id,
                                status: HelmetStatus, firmware: str) -> Helmet:
    result = await db.execute(select(Helmet).where(Helmet.helmet_code == code))
    h = result.scalar_one_or_none()
    if h:
        return h
    h = Helmet(helmet_code=code, zone=zone, gateway_id=gateway_id,
               worker_id=worker_id, status=status, firmware_version=firmware,
               is_active=True, last_seen=rand_dt(1))
    db.add(h)
    await db.flush()
    return h


# ── seed functions ────────────────────────────────────────────────────────────

async def seed_users_and_supervisors(db: AsyncSession):
    sup_users = [
        ("supervisor1@smarthelmet.com", "Alice Nkurunziza", "sup123", "+250788001001"),
        ("supervisor2@smarthelmet.com", "Bob Habimana",     "sup123", "+250788001002"),
    ]
    supervisors = []
    for i, (email, name, pwd, phone) in enumerate(sup_users, start=1):
        u = await get_or_create_user(db, email, name, pwd, UserRole.supervisor)
        s = await get_or_create_supervisor(db, f"SUP-{i:03d}", name, phone, u.id)
        supervisors.append(s)
    print(f"  supervisors: {len(supervisors)}")
    return supervisors


async def seed_workers(db: AsyncSession, supervisors):
    workers_data = [
        ("Jean Uwimana",    "WRK-001", "+250788002001", ZONES[0], supervisors[0].id),
        ("Marie Mukamana",  "WRK-002", "+250788002002", ZONES[0], supervisors[0].id),
        ("Eric Nshimiyimana","WRK-003", "+250788002003", ZONES[1], supervisors[0].id),
        ("Grace Uwineza",   "WRK-004", "+250788002004", ZONES[1], supervisors[1].id),
        ("Patrick Bizimana","WRK-005", "+250788002005", ZONES[2], supervisors[1].id),
        ("Claudine Ingabire","WRK-006", "+250788002006", ZONES[3], supervisors[1].id),
    ]
    workers = []
    for name, emp_id, phone, zone, sup_id in workers_data:
        email = f"{emp_id.lower()}@smarthelmet.com"
        u = await get_or_create_user(db, email, name, "worker123", UserRole.worker)
        w = await get_or_create_worker(db, emp_id, name, phone, zone, sup_id, u.id)
        workers.append(w)
    print(f"  workers: {len(workers)}")
    return workers


async def seed_gateways(db: AsyncSession):
    gateways_data = [
        ("Gateway Alpha", "Mining Level 1",   "192.168.1.10", True,  98.5),
        ("Gateway Beta",  "Chemical Plant B", "192.168.1.11", True,  95.2),
        ("Gateway Gamma", "Welding Bay C",    "192.168.1.12", False, 61.0),
    ]
    gateways = []
    for name, loc, ip, online, pdr in gateways_data:
        gw = await get_or_create_gateway(db, name, loc, ip, online, pdr)
        gateways.append(gw)
    print(f"  gateways: {len(gateways)}")
    return gateways


async def seed_supervisor_gateways(db: AsyncSession, supervisors, gateways):
    pairs = [
        (supervisors[0].id, gateways[0].id),
        (supervisors[0].id, gateways[1].id),
        (supervisors[1].id, gateways[1].id),
        (supervisors[1].id, gateways[2].id),
    ]
    for sup_id, gw_id in pairs:
        exists = await db.execute(
            select(supervisor_gateways).where(
                supervisor_gateways.c.supervisor_id == sup_id,
                supervisor_gateways.c.gateway_id == gw_id,
            )
        )
        if not exists.first():
            await db.execute(
                insert(supervisor_gateways).values(supervisor_id=sup_id, gateway_id=gw_id)
            )
    print(f"  supervisor-gateway links: {len(pairs)}")


async def seed_helmets(db: AsyncSession, workers, gateways):
    helmets_data = [
        ("HLM-A001", ZONES[0], gateways[0].id, workers[0].id, HelmetStatus.active,   "v2.1.0"),
        ("HLM-A002", ZONES[0], gateways[0].id, workers[1].id, HelmetStatus.active,   "v2.1.0"),
        ("HLM-B001", ZONES[1], gateways[1].id, workers[2].id, HelmetStatus.warning,  "v2.0.5"),
        ("HLM-B002", ZONES[1], gateways[1].id, workers[3].id, HelmetStatus.active,   "v2.1.0"),
        ("HLM-C001", ZONES[2], gateways[2].id, workers[4].id, HelmetStatus.critical, "v2.0.5"),
        ("HLM-C002", ZONES[2], gateways[2].id, workers[5].id, HelmetStatus.inactive, "v1.9.2"),
        ("HLM-D001", ZONES[3], None,            None,          HelmetStatus.inactive, "v2.1.0"),
        ("HLM-D002", ZONES[3], gateways[0].id, None,          HelmetStatus.active,   "v2.1.0"),
    ]
    helmets = []
    for code, zone, gw_id, w_id, status, fw in helmets_data:
        h = await get_or_create_helmet(db, code, zone, gw_id, w_id, status, fw)
        helmets.append(h)
    print(f"  helmets: {len(helmets)}")
    return helmets


async def seed_sensor_data(db: AsyncSession, helmets):
    total = 0
    now = datetime.utcnow()
    for helmet in helmets:
        readings_count = random.randint(20, 35)
        for i in range(readings_count):
            recorded_at = now - timedelta(hours=i * random.uniform(0.5, 3))

            # Vary co_ppm based on helmet status
            if helmet.status == HelmetStatus.critical:
                co = round(random.uniform(180, 280), 1)
            elif helmet.status == HelmetStatus.warning:
                co = round(random.uniform(45, 110), 1)
            else:
                co = round(random.uniform(5, 45), 1)

            ch4 = round(random.uniform(0.1, 0.8 if helmet.status == HelmetStatus.active else 1.8), 2)
            temp = round(random.uniform(24, 38), 1)
            humidity = round(random.uniform(50, 85), 1)
            helmet_worn = random.random() > 0.1
            vibration = random.random() < 0.05
            gas_level = int(co * 4 + random.randint(-10, 10))

            reading = SensorData(
                helmet_id=helmet.id,
                co_ppm=co,
                ch4_percent=ch4,
                temperature=temp,
                humidity=humidity,
                helmet_worn=helmet_worn,
                vibration_detected=vibration,
                gas_level=max(0, gas_level),
                accelerometer_x=round(random.uniform(-0.5, 0.5), 3),
                accelerometer_y=round(random.uniform(-0.5, 0.5), 3),
                accelerometer_z=round(random.uniform(9.5, 10.1), 3),
                battery_level=round(random.uniform(30, 100), 1),
                signal_strength=random.randint(-90, -40),
                recorded_at=recorded_at,
            )
            db.add(reading)
            total += 1

    print(f"  sensor readings: {total}")


async def seed_alerts(db: AsyncSession, helmets):
    alert_templates = [
        (AlertLevel.critical, AlertType.gas,        "Critical CO level: 245.0 ppm (threshold: 200 ppm)"),
        (AlertLevel.critical, AlertType.fall,        "Impact/fall detected"),
        (AlertLevel.warning,  AlertType.gas,         "Elevated CO level: 78.3 ppm (threshold: 50 ppm)"),
        (AlertLevel.warning,  AlertType.helmet_off,  "Helmet not being worn"),
        (AlertLevel.warning,  AlertType.temperature, "High temperature: 42.5°C"),
        (AlertLevel.critical, AlertType.temperature, "Critical temperature: 58.1°C"),
        (AlertLevel.warning,  AlertType.gas,         "Elevated CH4 level: 1.35% (threshold: 1.0%)"),
        (AlertLevel.info,     AlertType.multi,       "Multiple sensor anomalies detected"),
    ]

    total = 0
    now = datetime.utcnow()
    active_helmets = [h for h in helmets if h.worker_id is not None]

    for i, (level, atype, message) in enumerate(alert_templates):
        helmet = active_helmets[i % len(active_helmets)]
        created = now - timedelta(hours=random.randint(1, 72))
        is_resolved = random.random() < 0.4
        alert = Alert(
            level=level,
            type=atype,
            message=message,
            helmet_id=helmet.id,
            worker_id=helmet.worker_id,
            is_resolved=is_resolved,
            resolved_at=created + timedelta(minutes=random.randint(5, 120)) if is_resolved else None,
            resolved_by="admin@smarthelmet.com" if is_resolved else None,
            created_at=created,
        )
        db.add(alert)
        total += 1

    # Add a few more unresolved recent alerts for dashboard impact
    for helmet in active_helmets[:3]:
        for _ in range(2):
            db.add(Alert(
                level=random.choice([AlertLevel.warning, AlertLevel.critical]),
                type=random.choice([AlertType.gas, AlertType.fall, AlertType.helmet_off]),
                message="Sensor threshold breach detected",
                helmet_id=helmet.id,
                worker_id=helmet.worker_id,
                is_resolved=False,
                created_at=now - timedelta(minutes=random.randint(5, 120)),
            ))
            total += 1

    print(f"  alerts: {total}")


async def seed_notifications(db: AsyncSession, users: list[User], helmets):
    templates = [
        (NotificationType.critical, "Critical CO Alert",       "CO level exceeded 200 ppm on helmet HLM-C001"),
        (NotificationType.warning,  "Elevated Gas Level",      "CH4 level above warning threshold on helmet HLM-B001"),
        (NotificationType.warning,  "Helmet Not Worn",         "Worker Patrick Bizimana is not wearing their helmet"),
        (NotificationType.critical, "Fall Detected",           "Impact/fall detected on helmet HLM-C001 — check on worker"),
        (NotificationType.info,     "Gateway Offline",         "Gateway Gamma went offline at 14:32"),
        (NotificationType.success,  "Alert Resolved",          "CO alert for HLM-B002 has been resolved"),
        (NotificationType.warning,  "High Temperature",        "Temperature exceeded 42°C on helmet HLM-A002"),
        (NotificationType.info,     "New Worker Assigned",     "Worker Jean Uwimana assigned to helmet HLM-A001"),
        (NotificationType.info,     "System Health Check",     "CPU usage has been above 80% for the last 15 minutes"),
        (NotificationType.success,  "Firmware Update",         "Helmet HLM-A001 successfully updated to v2.1.0"),
    ]

    total = 0
    now = datetime.utcnow()
    active_helmets = [h for h in helmets if h.worker_id is not None]

    for user in users:
        for i, (ntype, title, message) in enumerate(templates):
            existing = await db.execute(
                select(Notification).where(
                    Notification.user_id == user.id,
                    Notification.title == title,
                )
            )
            if existing.scalar_one_or_none():
                continue
            helmet = active_helmets[i % len(active_helmets)] if active_helmets else None
            db.add(Notification(
                user_id=user.id,
                title=title,
                message=message,
                type=ntype,
                is_read=random.random() < 0.4,
                related_helmet_id=helmet.id if helmet else None,
                created_at=now - timedelta(hours=random.randint(1, 72)),
            ))
            total += 1

    print(f"  notifications: {total}")


async def seed_system_health(db: AsyncSession):
    existing = (await db.execute(
        select(SystemHealthLog).limit(1)
    )).scalar_one_or_none()
    if existing:
        print("  system_health_logs: already seeded, skipped")
        return

    now = datetime.utcnow()
    total = 0
    cpu_base    = random.uniform(30, 55)
    memory_base = random.uniform(45, 65)
    disk_base   = random.uniform(38, 50)

    for h in range(24 * 7):  # 7 days of hourly readings
        recorded_at = now - timedelta(hours=h)
        # Simulate realistic drift
        cpu_base    += random.uniform(-3, 3)
        memory_base += random.uniform(-1, 1)
        disk_base   += random.uniform(-0.1, 0.15)

        db.add(SystemHealthLog(
            cpu_percent=    round(max(5,  min(95,  cpu_base)),    1),
            memory_percent= round(max(20, min(90,  memory_base)), 1),
            disk_percent=   round(max(10, min(85,  disk_base)),   1),
            recorded_at=recorded_at,
        ))
        total += 1

    print(f"  system_health_logs: {total}")


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    print("Seeding database...")
    async with AsyncSessionLocal() as db:
        try:
            supervisors = await seed_users_and_supervisors(db)
            workers     = await seed_workers(db, supervisors)
            gateways    = await seed_gateways(db)
            await seed_supervisor_gateways(db, supervisors, gateways)
            helmets     = await seed_helmets(db, workers, gateways)
            await seed_sensor_data(db, helmets)
            await seed_alerts(db, helmets)

            # Fetch all non-admin users for notifications
            result = await db.execute(select(User))
            all_users = result.scalars().all()
            await seed_notifications(db, all_users, helmets)
            await seed_system_health(db)

            await db.commit()
            print("Done.")
        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
