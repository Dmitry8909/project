import asyncio
import re
from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.config import get_settings
from shared.models import User
from app.deps import get_db

router = APIRouter()

BCRYPT_ROUNDS = 8


async def async_hashpw(password: str) -> str:
    return await asyncio.to_thread(
        lambda: bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode(),
    )


async def async_checkpw(password: str, hashed: str) -> bool:
    return await asyncio.to_thread(
        lambda: bcrypt.checkpw(password.encode(), hashed.encode()),
    )


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 30:
            raise ValueError("Username must be at most 30 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, digits, and underscores")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    hashed = await async_hashpw(req.password)
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hashed,
        display_name=req.display_name or req.username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user_id=str(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not await async_checkpw(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token, user_id=str(user.id))
