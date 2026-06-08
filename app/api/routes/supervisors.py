import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.supervisor import SupervisorCreate, SupervisorUpdate, SupervisorResponse
from app.schemas.worker import WorkerResponse
from app.schemas.gateway import GatewayResponse
from app.core.dependencies import get_current_active_user
from app.models.supervisor import Supervisor
from app.models.worker import Worker
from app.models.gateway import Gateway
from app.db.base import supervisor_gateways

router = APIRouter()


def _supervisor_query():
    return select(Supervisor).options(selectinload(Supervisor.user))


def _worker_query():
    return select(Worker).options(selectinload(Worker.user))


@router.get("/", response_model=List[SupervisorResponse])
async def list_supervisors(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_supervisor_query().offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=SupervisorResponse, status_code=201)
async def add_supervisor(
    data: SupervisorCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    supervisor = Supervisor(**data.model_dump())
    db.add(supervisor)
    await db.commit()
    result = await db.execute(_supervisor_query().where(Supervisor.id == supervisor.id))
    return result.scalar_one()


@router.get("/{supervisor_id}", response_model=SupervisorResponse)
async def read_supervisor(
    supervisor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_supervisor_query().where(Supervisor.id == supervisor_id))
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return supervisor


@router.patch("/{supervisor_id}", response_model=SupervisorResponse)
async def edit_supervisor(
    supervisor_id: uuid.UUID,
    data: SupervisorUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_supervisor_query().where(Supervisor.id == supervisor_id))
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supervisor, field, value)
    await db.commit()
    result = await db.execute(_supervisor_query().where(Supervisor.id == supervisor_id))
    return result.scalar_one()


@router.delete("/{supervisor_id}", status_code=204)
async def remove_supervisor(
    supervisor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Supervisor).where(Supervisor.id == supervisor_id))
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    await db.delete(supervisor)
    await db.commit()


@router.get("/{supervisor_id}/workers", response_model=List[WorkerResponse])
async def supervisor_workers(
    supervisor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        _worker_query().where(Worker.supervisor_id == supervisor_id)
    )
    return result.scalars().all()


@router.get("/{supervisor_id}/gateways", response_model=List[GatewayResponse])
async def supervisor_gateways_route(
    supervisor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Gateway)
        .join(supervisor_gateways, Gateway.id == supervisor_gateways.c.gateway_id)
        .where(supervisor_gateways.c.supervisor_id == supervisor_id)
    )
    return result.scalars().all()
