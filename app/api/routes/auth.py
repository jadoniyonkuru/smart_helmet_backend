from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest, TokenResponse, UserCreate, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    ChangePasswordRequest, UpdateMeRequest,
)
from app.services.auth_service import (
    authenticate_user, register_user, forgot_password, reset_password,
)
from app.core.dependencies import get_current_active_user
from app.core.security import verify_password, hash_password
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await register_user(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await authenticate_user(db, data)


@router.post("/logout")
async def logout(_=Depends(get_current_active_user)):
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
async def forgot_password_route(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    await forgot_password(db, data.email)
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password_route(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await reset_password(db, data.token, data.new_password)
    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UpdateMeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.email is not None:
        existing = (await db.execute(
            select(User).where(User.email == data.email, User.id != current_user.id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = data.email
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/avatar")
async def upload_avatar_simple(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    upload_dir = Path("uploads/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{current_user.id}{ext}"
    file_path = upload_dir / filename
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    current_user.avatar_url = f"/uploads/avatars/{filename}"
    await db.commit()
    return {"avatar_url": current_user.avatar_url}


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (jpeg, png, gif, etc.)")

    upload_dir = Path("uploads/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{current_user.id}{ext}"
    file_path = upload_dir / filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    await db.commit()
    await db.refresh(current_user)
    return current_user
