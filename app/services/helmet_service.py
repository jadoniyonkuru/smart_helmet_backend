import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.models.helmet import Helmet
from app.models.worker import Worker
from app.schemas.helmet import HelmetCreate, HelmetUpdate


def _helmet_query():
    return select(Helmet).options(selectinload(Helmet.worker))


async def get_all_helmets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    assigned: Optional[bool] = None,
    supervisor_id: Optional[uuid.UUID] = None,
):
    q = _helmet_query()
    if assigned is True:
        q = q.where(Helmet.worker_id.isnot(None))
    elif assigned is False:
        q = q.where(Helmet.worker_id.is_(None))
    if supervisor_id is not None:
        q = q.join(Worker, Helmet.worker_id == Worker.id).where(
            Worker.supervisor_id == supervisor_id
        )
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


async def get_helmet(db: AsyncSession, helmet_id: uuid.UUID) -> Helmet:
    result = await db.execute(_helmet_query().where(Helmet.id == helmet_id))
    helmet = result.scalar_one_or_none()
    if not helmet:
        raise HTTPException(status_code=404, detail="Helmet not found")
    return helmet


async def create_helmet(db: AsyncSession, data: HelmetCreate) -> Helmet:
    result = await db.execute(
        select(Helmet).where(Helmet.helmet_code == data.helmet_code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Helmet code already exists")
    helmet = Helmet(**data.model_dump())
    db.add(helmet)
    await db.commit()
    result = await db.execute(_helmet_query().where(Helmet.id == helmet.id))
    return result.scalar_one()


async def update_helmet(db: AsyncSession, helmet_id: uuid.UUID, data: HelmetUpdate) -> Helmet:
    helmet = await get_helmet(db, helmet_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(helmet, field, value)
    await db.commit()
    result = await db.execute(_helmet_query().where(Helmet.id == helmet.id))
    return result.scalar_one()


async def delete_helmet(db: AsyncSession, helmet_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Helmet)
        .options(selectinload(Helmet.sensor_data), selectinload(Helmet.alerts))
        .where(Helmet.id == helmet_id)
    )
    helmet = result.scalar_one_or_none()
    if not helmet:
        raise HTTPException(status_code=404, detail="Helmet not found")
    await db.delete(helmet)
    await db.commit()
