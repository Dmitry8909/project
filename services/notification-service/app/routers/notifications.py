from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.models import Notification
from app.deps import get_db, get_current_user_id

router = APIRouter()


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    content: str | None
    reference_id: str | None
    is_read: bool
    created_at: str


@router.get("", response_model=list[NotificationResponse])
async def get_notifications(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = False,
):
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        NotificationResponse(
            id=str(n.id),
            type=n.type,
            title=n.title,
            content=n.content,
            reference_id=str(n.reference_id) if n.reference_id else None,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    return {"detail": "Marked as read"}


@router.post("/read-all")
async def mark_all_as_read(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"detail": "All notifications marked as read"}


@router.get("/unread-count")
async def unread_count(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    count = len(result.scalars().all())
    return {"count": count}
