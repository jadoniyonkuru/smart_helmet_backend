"""
purge_seed_data.py — Remove all seeded/mock data from the database.

Keeps:
  - Real IoT helmets (any helmet NOT in the seeded codes list)
  - Real workers (any worker NOT in the seeded employee_id list)
  - Real gateway "Gateway USB Demo"
  - Admin & supervisor user accounts
  - All real sensor readings (those belonging to kept helmets)

Run with:
    python -m scripts.purge_seed_data
"""
import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.alert import Alert
from app.models.gateway import Gateway
from app.models.helmet import Helmet
from app.models.notification import Notification
from app.models.sensor_data import SensorData
from app.models.user import User, UserRole
from app.models.worker import Worker

# ── The codes/IDs that were created by seed.py ─────────────────────────────

SEEDED_HELMET_CODES = {
    "HLM-A001", "HLM-A002",
    "HLM-B001", "HLM-B002",
    "HLM-C001", "HLM-C002",
    "HLM-D001", "HLM-D002",
}

SEEDED_WORKER_IDS = {
    "WRK-001", "WRK-002", "WRK-003",
    "WRK-004", "WRK-005", "WRK-006",
}

SEEDED_GATEWAY_NAMES = {
    "Gateway Alpha", "Gateway Beta", "Gateway Gamma",
}

SEEDED_WORKER_EMAILS = {
    "wrk-001@smarthelmet.com",
    "wrk-002@smarthelmet.com",
    "wrk-003@smarthelmet.com",
    "wrk-004@smarthelmet.com",
    "wrk-005@smarthelmet.com",
    "wrk-006@smarthelmet.com",
}

# ───────────────────────────────────────────────────────────────────────────

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def main():
    print("=" * 55)
    print("  SafeHelm — Purge Seed Data")
    print("=" * 55)

    async with AsyncSessionLocal() as db:
        try:
            # ── 1. Find seeded helmet IDs ─────────────────────────
            print("\n[1] Locating seeded helmets...")
            result = await db.execute(
                select(Helmet).where(Helmet.helmet_code.in_(SEEDED_HELMET_CODES))
            )
            seeded_helmets = result.scalars().all()
            seeded_helmet_ids = [h.id for h in seeded_helmets]
            print(f"    Found {len(seeded_helmet_ids)} seeded helmets: "
                  f"{[h.helmet_code for h in seeded_helmets]}")

            # ── 2. Find seeded worker IDs ─────────────────────────
            print("\n[2] Locating seeded workers...")
            result = await db.execute(
                select(Worker).where(Worker.employee_id.in_(SEEDED_WORKER_IDS))
            )
            seeded_workers = result.scalars().all()
            seeded_worker_ids = [w.id for w in seeded_workers]
            print(f"    Found {len(seeded_worker_ids)} seeded workers: "
                  f"{[w.full_name for w in seeded_workers]}")

            if not seeded_helmet_ids and not seeded_worker_ids:
                print("\n  Nothing to purge — seed data not found in database.")
                return

            # ── 3. Delete sensor readings for seeded helmets ──────
            if seeded_helmet_ids:
                print("\n[3] Deleting sensor readings...")
                r = await db.execute(
                    delete(SensorData).where(SensorData.helmet_id.in_(seeded_helmet_ids))
                )
                print(f"    Deleted {r.rowcount} sensor readings")

            # ── 4. Delete notifications referencing seeded helmets ─
            print("\n[4] Deleting seeded notifications...")
            if seeded_helmet_ids:
                r = await db.execute(
                    delete(Notification).where(
                        Notification.related_helmet_id.in_(seeded_helmet_ids)
                    )
                )
                print(f"    Deleted {r.rowcount} notifications (helmet-linked)")

            # ── 5. Delete alerts for seeded helmets / workers ─────
            print("\n[5] Deleting seeded alerts...")
            deleted_alerts = 0
            if seeded_helmet_ids:
                r = await db.execute(
                    delete(Alert).where(Alert.helmet_id.in_(seeded_helmet_ids))
                )
                deleted_alerts += r.rowcount
            if seeded_worker_ids:
                r = await db.execute(
                    delete(Alert).where(Alert.worker_id.in_(seeded_worker_ids))
                )
                deleted_alerts += r.rowcount
            print(f"    Deleted {deleted_alerts} alerts")

            # ── 6. Delete seeded helmets ──────────────────────────
            if seeded_helmet_ids:
                print("\n[6] Deleting seeded helmets...")
                r = await db.execute(
                    delete(Helmet).where(Helmet.id.in_(seeded_helmet_ids))
                )
                print(f"    Deleted {r.rowcount} helmets")

            # ── 7. Delete seeded workers ──────────────────────────
            if seeded_worker_ids:
                print("\n[7] Deleting seeded workers...")
                r = await db.execute(
                    delete(Worker).where(Worker.id.in_(seeded_worker_ids))
                )
                print(f"    Deleted {r.rowcount} workers")

            # ── 8. Delete seeded user accounts (worker logins only) ─
            print("\n[8] Deleting seeded worker user accounts...")
            result = await db.execute(
                select(User).where(User.email.in_(SEEDED_WORKER_EMAILS))
            )
            seeded_users = result.scalars().all()
            seeded_user_ids = [u.id for u in seeded_users]
            if seeded_user_ids:
                # Remove any leftover notifications for these users first
                await db.execute(
                    delete(Notification).where(Notification.user_id.in_(seeded_user_ids))
                )
                r = await db.execute(
                    delete(User).where(User.id.in_(seeded_user_ids))
                )
                print(f"    Deleted {r.rowcount} worker user accounts")
            else:
                print("    No seeded worker accounts found")

            # ── 9. Delete seeded gateways ─────────────────────────
            print("\n[9] Deleting seeded gateways...")
            r = await db.execute(
                delete(Gateway).where(Gateway.name.in_(SEEDED_GATEWAY_NAMES))
            )
            print(f"    Deleted {r.rowcount} gateways")

            # ── Commit ────────────────────────────────────────────
            await db.commit()

            print("\n" + "=" * 55)
            print("  Done! Database now contains only real device data.")
            print("=" * 55)
            print("\n  Preserved:")
            print("  - Admin & supervisor user accounts")
            print("  - Real IoT helmet (code: '1') and its readings")
            print("  - Real worker (REAL-WRK-001)")
            print("  - Gateway USB Demo")

        except Exception as e:
            await db.rollback()
            print(f"\n  ERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
