import uuid
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.worker import WorkerCreate, WorkerUpdate, WorkerResponse
from app.schemas.helmet import HelmetResponse
from app.schemas.supervisor import SupervisorResponse
from app.core.dependencies import get_current_active_user, require_admin
from app.core.security import hash_password
from app.models.worker import Worker
from app.models.helmet import Helmet
from app.models.alert import Alert
from app.models.user import User, UserRole
from app.models.supervisor import Supervisor
from app.services.email_service import send_worker_welcome_email

router = APIRouter()


def _worker_query():
    return select(Worker).options(
        selectinload(Worker.user),
        selectinload(Worker.dept),
    )


@router.get("/", response_model=List[WorkerResponse])
async def list_workers(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    q = _worker_query()
    # Supervisors only see workers assigned to them
    if current_user.role == UserRole.supervisor:
        sup = (await db.execute(
            select(Supervisor).where(Supervisor.user_id == current_user.id)
        )).scalar_one_or_none()
        if sup:
            q = q.where(Worker.supervisor_id == sup.id)
    if is_active is not None:
        q = q.where(Worker.is_active == is_active)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=WorkerResponse, status_code=201)
async def add_worker(
    data: WorkerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Auto-assign supervisor_id when the creator is a supervisor
    supervisor_id = data.supervisor_id
    if current_user.role == UserRole.supervisor and supervisor_id is None:
        sup = (await db.execute(
            select(Supervisor).where(Supervisor.user_id == current_user.id)
        )).scalar_one_or_none()
        if sup:
            supervisor_id = sup.id

    # If a supervisor_id was provided, ensure it exists
    if supervisor_id is not None:
        existing_sup = (await db.execute(
            select(Supervisor).where(Supervisor.id == supervisor_id)
        )).scalar_one_or_none()
        if not existing_sup:
            raise HTTPException(status_code=400, detail="Supervisor not found")

    user_id = data.user_id
    # Auto-create a User account when email is provided
    if data.email and not user_id:
        existing = (await db.execute(
            select(User).where(User.email == data.email)
        )).scalar_one_or_none()
        if existing:
            user_id = existing.id
        else:
            temp_password = secrets.token_urlsafe(12)
            new_user = User(
                email=data.email,
                full_name=data.full_name,
                hashed_password=hash_password(temp_password),
                role=UserRole.worker,
                is_active=True,
                is_verified=True,
            )
            db.add(new_user)
            await db.flush()
            user_id = new_user.id

    worker = Worker(
        full_name=data.full_name,
        employee_id=data.employee_id,
        phone=data.phone,
        zone=data.zone,
        supervisor_id=supervisor_id,
        user_id=user_id,
        department_id=data.department_id,
    )
    db.add(worker)
    await db.commit()

    result = await db.execute(_worker_query().where(Worker.id == worker.id))
    worker_out = result.scalar_one()

    # Send welcome email to the new worker
    if data.email:
        helmet_result = await db.execute(
            select(Helmet).where(Helmet.worker_id == worker.id).limit(1)
        )
        helmet = helmet_result.scalar_one_or_none()
        try:
            await send_worker_welcome_email(
                recipient=data.email,
                full_name=data.full_name,
                employee_id=data.employee_id,
                helmet_code=helmet.helmet_code if helmet else None,
            )
        except Exception:
            pass  # Don't fail the request if email delivery fails

    return worker_out


@router.get("/{worker_id}", response_model=WorkerResponse)
async def read_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(_worker_query().where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    # Supervisors can only view their own workers
    if current_user.role == UserRole.supervisor:
        sup = (await db.execute(
            select(Supervisor).where(Supervisor.user_id == current_user.id)
        )).scalar_one_or_none()
        if not sup or worker.supervisor_id != sup.id:
            raise HTTPException(status_code=403, detail="Access denied")
    return worker


@router.patch("/{worker_id}", response_model=WorkerResponse)
async def edit_worker(
    worker_id: uuid.UUID,
    data: WorkerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(_worker_query().where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    # Supervisors can only edit their own workers
    if current_user.role == UserRole.supervisor:
        sup = (await db.execute(
            select(Supervisor).where(Supervisor.user_id == current_user.id)
        )).scalar_one_or_none()
        if not sup or worker.supervisor_id != sup.id:
            raise HTTPException(status_code=403, detail="Access denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(worker, field, value)
    await db.commit()
    result = await db.execute(_worker_query().where(Worker.id == worker_id))
    return result.scalar_one()


@router.delete("/{worker_id}", status_code=204)
async def remove_worker(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    # Supervisors can only delete their own workers
    if current_user.role == UserRole.supervisor:
        sup = (await db.execute(
            select(Supervisor).where(Supervisor.user_id == current_user.id)
        )).scalar_one_or_none()
        if not sup or worker.supervisor_id != sup.id:
            raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(worker)
    await db.commit()


@router.post("/{worker_id}/promote", response_model=SupervisorResponse, status_code=201)
async def promote_worker_to_supervisor(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(_worker_query().where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not worker.user_id:
        raise HTTPException(
            status_code=400,
            detail="Worker has no account (email) and cannot be promoted",
        )

    existing_sup = (await db.execute(
        select(Supervisor).where(Supervisor.user_id == worker.user_id)
    )).scalar_one_or_none()
    if existing_sup:
        raise HTTPException(status_code=400, detail="This person is already a supervisor")

    employee_id = f"SUP-{uuid.uuid4().hex[:8].upper()}"
    supervisor = Supervisor(
        full_name=worker.full_name,
        employee_id=employee_id,
        phone=worker.phone,
        user_id=worker.user_id,
    )
    db.add(supervisor)

    user = (await db.execute(select(User).where(User.id == worker.user_id))).scalar_one()
    user.role = UserRole.supervisor

    # Free up anything still pointing at the worker row before deleting it
    await db.execute(
        Helmet.__table__.update().where(Helmet.worker_id == worker.id).values(worker_id=None)
    )
    await db.execute(
        Alert.__table__.update().where(Alert.worker_id == worker.id).values(worker_id=None)
    )
    await db.delete(worker)
    await db.commit()

    result = await db.execute(
        select(Supervisor)
        .options(selectinload(Supervisor.user), selectinload(Supervisor.workers))
        .where(Supervisor.id == supervisor.id)
    )
    return result.scalar_one()


@router.get("/{worker_id}/helmets", response_model=List[HelmetResponse])
async def worker_helmets(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Helmet).where(Helmet.worker_id == worker_id))
    return result.scalars().all()
