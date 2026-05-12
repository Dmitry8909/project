from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.models import Message, MessageMedia, User
from shared.rabbitmq import RabbitMQClient
from shared.config import get_settings
from app.deps import get_db, get_current_user_id

router = APIRouter()


class MediaItem(BaseModel):
    file_url: str
    file_type: str


class SendMessageRequest(BaseModel):
    receiver_id: str
    content: str = ""
    media: list[MediaItem] = []


class MessageMediaResponse(BaseModel):
    id: str
    file_url: str
    file_type: str
    order: int


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    receiver_id: str
    content: str
    media: list[MessageMediaResponse] = []
    is_read: bool
    created_at: str


class ConversationResponse(BaseModel):
    user_id: str
    username: str
    display_name: str | None
    avatar_url: str | None
    last_message: str
    last_message_at: str
    has_media: bool = False
    unread_count: int


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    req: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not req.content.strip() and not req.media:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content or media is required",
        )

    if user_id == req.receiver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself",
        )

    message = Message(
        sender_id=user_id,
        receiver_id=req.receiver_id,
        content=req.content,
    )
    db.add(message)
    await db.flush()

    for i, m in enumerate(req.media):
        mm = MessageMedia(
            message_id=message.id,
            file_url=m.file_url,
            file_type=m.file_type,
            order=i,
        )
        db.add(mm)

    await db.commit()
    await db.refresh(message)

    try:
        settings = get_settings()
        result = await db.execute(select(User).where(User.id == user_id))
        sender = result.scalar_one_or_none()
        sender_name = sender.display_name or sender.username if sender else "Someone"

        receiver_pref = await db.execute(
            select(User.receive_new_message_notifications).where(User.id == req.receiver_id)
        )
        if receiver_pref.scalar_one_or_none():
            rmq = RabbitMQClient(settings.rabbitmq_url)
            preview = req.content[:100] if req.content.strip() else "[Photo]"
            await rmq.publish(
                "notifications",
                "new_message",
                {
                    "type": "new_message",
                    "user_id": req.receiver_id,
                    "sender_id": user_id,
                    "actor_name": sender_name,
                    "message_id": str(message.id),
                    "content_preview": preview,
                },
            )
            await rmq.close()
    except Exception:
        pass

    return _message_to_response(message)


@router.get("/conversation/{other_user_id}", response_model=list[MessageResponse])
async def get_conversation(
    other_user_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(Message)
        .where(
            or_(
                and_(Message.sender_id == user_id, Message.receiver_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.receiver_id == user_id),
            )
        )
        .options(selectinload(Message.media))
        .order_by(Message.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()

    unread_ids = [
        m.id for m in messages
        if str(m.receiver_id) == user_id and not m.is_read
    ]
    if unread_ids:
        for msg in messages:
            if msg.id in unread_ids:
                msg.is_read = True
        await db.commit()

        try:
            settings = get_settings()
            rmq = RabbitMQClient(settings.rabbitmq_url)
            await rmq.publish("notifications", "read_receipt", {
                "type": "read_receipt",
                "user_id": other_user_id,
                "conversation_with": user_id,
                "message_ids": [str(i) for i in unread_ids],
            })
            await rmq.close()
        except Exception:
            pass

    messages.reverse()
    return [_message_to_response(m) for m in messages]


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(
            or_(
                Message.sender_id == user_id,
                Message.receiver_id == user_id,
            )
        )
        .options(selectinload(Message.media))
        .order_by(Message.created_at.desc())
    )
    all_messages = result.scalars().all()

    user_cache: dict[str, User] = {}

    async def get_user(uid: str) -> User | None:
        if uid not in user_cache:
            r = await db.execute(select(User).where(User.id == uid))
            user_cache[uid] = r.scalar_one_or_none()
        return user_cache[uid]

    conversations: dict[str, dict] = {}
    for msg in all_messages:
        other_id = str(msg.receiver_id) if str(msg.sender_id) == user_id else str(msg.sender_id)
        if other_id not in conversations:
            other_user = await get_user(other_id)
            last_text = msg.content[:100] if msg.content.strip() else ""
            has_media = bool(msg.media)
            preview = last_text if last_text else ("[Photo]" if has_media else "")

            conversations[other_id] = {
                "user_id": other_id,
                "username": other_user.username if other_user else "Unknown",
                "display_name": other_user.display_name if other_user else None,
                "avatar_url": other_user.avatar_url if other_user else None,
                "last_message": preview,
                "last_message_at": msg.created_at.isoformat(),
                "has_media": has_media,
                "unread_count": 0,
            }
        if str(msg.receiver_id) == user_id and not msg.is_read:
            conversations[other_id]["unread_count"] += 1

    return list(conversations.values())


@router.get("/unread-count")
async def unread_messages_count(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message).where(
            Message.receiver_id == user_id,
            Message.is_read == False,
        )
    )
    messages = result.scalars().all()
    unique_senders = set(str(m.sender_id) for m in messages)
    return {"count": len(unique_senders)}


def _message_to_response(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=str(msg.id),
        sender_id=str(msg.sender_id),
        receiver_id=str(msg.receiver_id),
        content=msg.content,
        media=[
            MessageMediaResponse(
                id=str(m.id),
                file_url=m.file_url,
                file_type=m.file_type,
                order=m.order,
            )
            for m in (msg.media or [])
        ],
        is_read=msg.is_read,
        created_at=msg.created_at.isoformat(),
    )
