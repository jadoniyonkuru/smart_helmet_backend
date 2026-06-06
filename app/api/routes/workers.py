import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.worker import WorkerCreate, WorkerUpdate, WorkerResponse
from app.schemas.helmet import HelmetResponse
from app.core.dependencies import get_current_active_user
from app.models.worker import Worker
from app.models.helmet import Helmet

router = APIRouter()


@router.get("/", response_model=List[WorkerResponse])
async def list_workers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Worker).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=WorkerResponse, status_code=201)
async def add_worker(
    data: WorkerCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    worker = Worker(**data.model_dump())
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    return worker


@router.get("/{worker_id}", response_model=WorkerResponse)
async def read_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.patch("/{worker_id}", response_model=WorkerResponse)
async def edit_worker(
    worker_id: uuid.UUID,
    data: WorkerUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(worker, field, value)
    await db.commit()
    await db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=204)
async def remove_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    await db.delete(worker)
    await db.commit()


@router.get("/{worker_id}/helmets", response_model=List[HelmetResponse])
async def worker_helmets(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Helmet).where(Helmet.worker_id == worker_id))
    return result.scalars().all()
