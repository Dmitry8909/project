import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, func, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "id", name="pk_notifications"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
