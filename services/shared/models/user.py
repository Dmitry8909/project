import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(100))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    show_dob: Mapped[bool] = mapped_column(Boolean, default=True)
    likes_public: Mapped[bool] = mapped_column(Boolean, default=False)
    receive_new_post_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    receive_like_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    receive_follow_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    receive_new_message_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    receive_comment_mention_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    posts = relationship("Post", back_populates="author", lazy="selectin")
    followers = relationship(
        "Subscription",
        foreign_keys="Subscription.following_id",
        back_populates="following",
        lazy="selectin",
    )
    following = relationship(
        "Subscription",
        foreign_keys="Subscription.follower_id",
        back_populates="follower",
        lazy="selectin",
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")
