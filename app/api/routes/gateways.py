import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.gateway import GatewayCreate, GatewayUpdate, GatewayResponse
from app.schemas.helmet import HelmetResponse
from app.core.dependencies import get_current_active_user
from app.models.gateway import Gateway
from app.models.helmet import Helmet

router = APIRouter()


def _gateway_query():
    return select(Gateway).options(selectinload(Gateway.helmets))


@router.get("/", response_model=List[GatewayResponse])
async def list_gateways(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_gateway_query().offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=GatewayResponse, status_code=201)
async def add_gateway(
    data: GatewayCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    gateway_data = data.model_dump(exclude={'status'})
    if data.status is not None:
        gateway_data['is_online'] = data.status == 'online'
    gateway = Gateway(**gateway_data)
    db.add(gateway)
    await db.commit()
    result = await db.execute(_gateway_query().where(Gateway.id == gateway.id))
    return result.scalar_one()


@router.get("/{gateway_id}", response_model=GatewayResponse)
async def read_gateway(
    gateway_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_gateway_query().where(Gateway.id == gateway_id))
    gateway = result.scalar_one_or_none()
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return gateway


@router.patch("/{gateway_id}", response_model=GatewayResponse)
async def edit_gateway(
    gateway_id: uuid.UUID,
    data: GatewayUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_gateway_query().where(Gateway.id == gateway_id))
    gateway = result.scalar_one_or_none()
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
    update_data = data.model_dump(exclude_unset=True, exclude={'status'})
    if data.status is not None:
        update_data['is_online'] = data.status == 'online'
    for field, value in update_data.items():
        setattr(gateway, field, value)
    await db.commit()
    result = await db.execute(_gateway_query().where(Gateway.id == gateway_id))
    return result.scalar_one()


@router.delete("/{gateway_id}", status_code=204)
async def remove_gateway(
    gateway_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Gateway).where(Gateway.id == gateway_id))
    gateway = result.scalar_one_or_none()
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
    await db.delete(gateway)
    await db.commit()


@router.get("/{gateway_id}/status")
async def gateway_status(
    gateway_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_gateway_query().where(Gateway.id == gateway_id))
    gateway = result.scalar_one_or_none()
    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return {
        "id": str(gateway.id),
        "name": gateway.name,
        "is_online": gateway.is_online,
        "status": gateway.status,
        "location": gateway.location,
        "ip_address": gateway.ip_address,
        "last_seen": gateway.last_seen,
        "packet_delivery_rate": gateway.packet_delivery_rate,
        "connected_helmets": gateway.connected_helmets,
    }


@router.get("/{gateway_id}/helmets", response_model=List[HelmetResponse])
async def gateway_helmets(
    gateway_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Helmet).where(Helmet.gateway_id == gateway_id))
    return result.scalars().all()
