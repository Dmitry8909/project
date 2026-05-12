import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, func, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        PrimaryKeyConstraint("sender_id", "id", name="pk_messages"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    media = relationship(
        "MessageMedia",
        primaryjoin="MessageMedia.message_id == Message.id",
        foreign_keys="MessageMedia.message_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class MessageMedia(Base):
    __tablename__ = "message_media"
    __table_args__ = (
        PrimaryKeyConstraint("message_id", "id", name="pk_message_media"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
