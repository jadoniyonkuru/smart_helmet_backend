import uuid
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.supervisor import SupervisorCreate, SupervisorUpdate, SupervisorResponse
from app.schemas.worker import WorkerResponse
from app.core.dependencies import get_current_active_user, require_admin
from app.core.security import hash_password
from app.models.supervisor import Supervisor
from app.models.user import User, UserRole
from app.models.worker import Worker
from app.services.email_service import send_welcome_email

router = APIRouter()


def _supervisor_query():
    return select(Supervisor).options(
        selectinload(Supervisor.user),
        selectinload(Supervisor.workers),
    )


def _worker_query():
    return select(Worker).options(selectinload(Worker.user), selectinload(Worker.dept))


@router.get("/", response_model=List[SupervisorResponse])
async def list_supervisors(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    q = _supervisor_query()
    if is_active is not None:
        q = q.where(Supervisor.is_active == is_active)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=SupervisorResponse, status_code=201)
async def add_supervisor(
    data: SupervisorCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    existing_user = (await db.execute(
        select(User).where(User.email == data.email)
    )).scalar_one_or_none()

    reset_token = None
    if existing_user:
        user = existing_user
        if user.role != UserRole.supervisor:
            raise HTTPException(
                status_code=400,
                detail="A user with this email already exists with a different role.",
            )
    else:
        temp_password = secrets.token_urlsafe(12)
        reset_token = secrets.token_urlsafe(32)
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(temp_password),
            role=UserRole.supervisor,
            is_active=True,
            is_verified=True,
            reset_token=reset_token,
        )
        db.add(user)
        await db.flush()

    employee_id = data.employee_id or f"SUP-{uuid.uuid4().hex[:8].upper()}"
    existing_emp = (await db.execute(
        select(Supervisor).where(Supervisor.employee_id == employee_id)
    )).scalar_one_or_none()
    if existing_emp:
        employee_id = f"SUP-{uuid.uuid4().hex[:8].upper()}"

    supervisor = Supervisor(
        full_name=data.full_name,
        employee_id=employee_id,
        phone=data.phone,
        user_id=user.id,
    )
    db.add(supervisor)
    await db.commit()

    # Send welcome email so the new supervisor can set their password
    if reset_token:
        try:
            await send_welcome_email(
                recipient=data.email,
                full_name=data.full_name,
                reset_token=reset_token,
            )
        except Exception:
            pass  # Don't fail the request if email delivery fails

    result = await db.execute(
        _supervisor_query().where(Supervisor.id == supervisor.id)
    )
    return result.scalar_one()


@router.get("/{supervisor_id}", response_model=SupervisorResponse)
async def read_supervisor(
    supervisor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        _supervisor_query().where(Supervisor.id == supervisor_id)
    )
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return supervisor


@router.patch("/{supervisor_id}", response_model=SupervisorResponse)
async def edit_supervisor(
    supervisor_id: uuid.UUID,
    data: SupervisorUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(
        _supervisor_query().where(Supervisor.id == supervisor_id)
    )
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supervisor, field, value)
    await db.commit()
    result = await db.execute(
        _supervisor_query().where(Supervisor.id == supervisor_id)
    )
    return result.scalar_one()


@router.delete("/{supervisor_id}", status_code=204)
async def remove_supervisor(
    supervisor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(
        select(Supervisor).where(Supervisor.id == supervisor_id)
    )
    supervisor = result.scalar_one_or_none()
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    await db.delete(supervisor)
    await db.commit()


@router.get("/{supervisor_id}/workers", response_model=List[WorkerResponse])
async def supervisor_workers(
    supervisor_id: uuid.UUID,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    q = _worker_query().where(Worker.supervisor_id == supervisor_id)
    if is_active is not None:
        q = q.where(Worker.is_active == is_active)
    result = await db.execute(q)
    return result.scalars().all()
