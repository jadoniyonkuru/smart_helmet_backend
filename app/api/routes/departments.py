import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.schemas.worker import WorkerResponse
from app.core.dependencies import get_current_active_user
from app.models.department import Department
from app.models.worker import Worker

router = APIRouter()


def _dept_query():
    return select(Department).options(selectinload(Department.workers))


@router.get("/", response_model=List[DepartmentResponse])
async def list_departments(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_dept_query().offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/", response_model=DepartmentResponse, status_code=201)
async def add_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    existing = (await db.execute(
        select(Department).where(Department.name == data.name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A department with this name already exists")

    dept = Department(**data.model_dump())
    db.add(dept)
    await db.commit()

    result = await db.execute(_dept_query().where(Department.id == dept.id))
    return result.scalar_one()


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def read_department(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_dept_query().where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.patch("/{dept_id}", response_model=DepartmentResponse)
async def edit_department(
    dept_id: uuid.UUID,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(_dept_query().where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    # Check name uniqueness if name is being changed
    if data.name and data.name != dept.name:
        conflict = (await db.execute(
            select(Department).where(Department.name == data.name)
        )).scalar_one_or_none()
        if conflict:
            raise HTTPException(status_code=400, detail="A department with this name already exists")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    await db.commit()

    result = await db.execute(_dept_query().where(Department.id == dept_id))
    return result.scalar_one()


@router.delete("/{dept_id}", status_code=204)
async def remove_department(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.delete(dept)
    await db.commit()


@router.get("/{dept_id}/workers", response_model=List[WorkerResponse])
async def department_workers(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Worker)
        .options(selectinload(Worker.user))
        .where(Worker.department_id == dept_id)
    )
    return result.scalars().all()
