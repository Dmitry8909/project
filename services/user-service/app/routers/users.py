from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.models import User, Subscription
from app.deps import get_db, get_current_user

router = APIRouter()


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    location: str | None
    date_of_birth: str | None
    show_dob: bool = True
    likes_public: bool = False
    receive_new_post_notifications: bool = True
    receive_like_notifications: bool = True
    receive_follow_notifications: bool = True
    receive_new_message_notifications: bool = True
    receive_comment_mention_notifications: bool = True
    followers_count: int = 0
    following_count: int = 0
    created_at: str


class UserSearchResponse(BaseModel):
    id: str
    username: str
    display_name: str | None
    avatar_url: str | None
    bio: str | None
    is_following: bool = False


class UserUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    location: str | None = None
    date_of_birth: str | None = None
    show_dob: bool | None = None
    likes_public: bool | None = None
    receive_new_post_notifications: bool | None = None
    receive_like_notifications: bool | None = None
    receive_follow_notifications: bool | None = None
    receive_new_message_notifications: bool | None = None
    receive_comment_mention_notifications: bool | None = None

    @field_validator("bio")
    @classmethod
    def bio_max_length(cls, v: str | None) -> str | None:
        if v and len(v) > 200:
            raise ValueError("Bio must not exceed 200 characters")
        return v


def _user_to_response(user: User, is_own: bool = False) -> UserResponse:
    dob = None
    if user.date_of_birth:
        if is_own or user.show_dob:
            dob = user.date_of_birth.isoformat()
    return UserResponse(
        id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        location=user.location,
        date_of_birth=dob,
        show_dob=user.show_dob,
        likes_public=user.likes_public,
        receive_new_post_notifications=user.receive_new_post_notifications,
        receive_like_notifications=user.receive_like_notifications,
        receive_follow_notifications=user.receive_follow_notifications,
        receive_new_message_notifications=user.receive_new_message_notifications,
        receive_comment_mention_notifications=user.receive_comment_mention_notifications,
        followers_count=len(user.followers),
        following_count=len(user.following),
        created_at=user.created_at.isoformat(),
    )


@router.get("/search", response_model=list[UserSearchResponse])
async def search_users(
    q: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    result = await db.execute(
        select(User)
        .where(
            or_(
                User.username.ilike(f"%{q}%"),
                User.display_name.ilike(f"%{q}%"),
            )
        )
        .limit(limit)
    )
    users = result.scalars().all()

    following_ids = set()
    following_result = await db.execute(
        select(Subscription.following_id).where(
            Subscription.follower_id == current_user.id
        )
    )
    for row in following_result.all():
        following_ids.add(str(row[0]))

    return [
        UserSearchResponse(
            id=str(u.id),
            username=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            bio=u.bio,
            is_following=str(u.id) in following_ids,
        )
        for u in users
    ]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return _user_to_response(current_user, is_own=True)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if update.display_name is not None:
        current_user.display_name = update.display_name
    if update.bio is not None:
        current_user.bio = update.bio
    if update.avatar_url is not None:
        current_user.avatar_url = update.avatar_url
    if update.location is not None:
        current_user.location = update.location
    if update.date_of_birth is not None:
        current_user.date_of_birth = date.fromisoformat(update.date_of_birth)
    if update.show_dob is not None:
        current_user.show_dob = update.show_dob
    if update.likes_public is not None:
        current_user.likes_public = update.likes_public
    if update.receive_new_post_notifications is not None:
        current_user.receive_new_post_notifications = update.receive_new_post_notifications
    if update.receive_like_notifications is not None:
        current_user.receive_like_notifications = update.receive_like_notifications
    if update.receive_follow_notifications is not None:
        current_user.receive_follow_notifications = update.receive_follow_notifications
    if update.receive_new_message_notifications is not None:
        current_user.receive_new_message_notifications = update.receive_new_message_notifications
    if update.receive_comment_mention_notifications is not None:
        current_user.receive_comment_mention_notifications = update.receive_comment_mention_notifications

    await db.commit()
    await db.refresh(current_user)

    return _user_to_response(current_user, is_own=True)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.followers), selectinload(User.following))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return _user_to_response(user, is_own=str(user.id) == str(current_user.id))


@router.get("/by-username/{username}", response_model=UserResponse)
async def get_user_by_username(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .where(User.username == username)
        .options(selectinload(User.followers), selectinload(User.following))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return _user_to_response(user, is_own=str(user.id) == str(current_user.id))
