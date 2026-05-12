from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.models import User, Subscription
from shared.rabbitmq import RabbitMQClient
from shared.config import get_settings
from app.deps import get_db, get_current_user

router = APIRouter()


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: str | None
    avatar_url: str | None


class FollowerResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: str | None
    avatar_url: str | None


@router.post("/follow/{user_id}", status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )

    target = await db.execute(select(User).where(User.id == user_id))
    target_user = target.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await db.execute(
        select(Subscription).where(
            Subscription.follower_id == current_user.id,
            Subscription.following_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already following this user",
        )

    sub = Subscription(follower_id=current_user.id, following_id=user_id)
    db.add(sub)
    await db.commit()

    try:
        if target_user.receive_follow_notifications:
            settings = get_settings()
            rmq = RabbitMQClient(settings.rabbitmq_url)
            await rmq.publish(
                "notifications",
                "follow",
                {
                    "type": "follow",
                    "user_id": user_id,
                    "actor_id": str(current_user.id),
                    "actor_name": current_user.display_name or current_user.username,
                },
            )
            await rmq.close()
    except Exception:
        pass

    return {"detail": "Followed successfully"}


@router.delete("/unfollow/{user_id}")
async def unfollow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(Subscription).where(
            Subscription.follower_id == current_user.id,
            Subscription.following_id == user_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user",
        )
    await db.commit()
    return {"detail": "Unfollowed successfully"}


@router.get("/following", response_model=list[SubscriptionResponse])
async def get_following(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.follower_id == current_user.id)
        .options(selectinload(Subscription.following))
    )
    subs = result.scalars().all()
    return [
        SubscriptionResponse(
            id=str(sub.id),
            user_id=str(sub.following.id),
            username=sub.following.username,
            display_name=sub.following.display_name,
            avatar_url=sub.following.avatar_url,
        )
        for sub in subs
    ]


@router.get("/followers", response_model=list[FollowerResponse])
async def get_followers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.following_id == current_user.id)
        .options(selectinload(Subscription.follower))
    )
    subs = result.scalars().all()
    return [
        FollowerResponse(
            id=str(sub.id),
            user_id=str(sub.follower.id),
            username=sub.follower.username,
            display_name=sub.follower.display_name,
            avatar_url=sub.follower.avatar_url,
        )
        for sub in subs
    ]
