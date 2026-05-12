import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, func, PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database import Base


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        PrimaryKeyConstraint("author_id", "id", name="pk_posts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    repost_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    author = relationship("User", back_populates="posts", lazy="selectin")
    media = relationship(
        "PostMedia",
        primaryjoin="PostMedia.post_id == Post.id",
        foreign_keys="PostMedia.post_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "Comment",
        primaryjoin="Comment.post_id == Post.id",
        foreign_keys="Comment.post_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    bookmarks = relationship(
        "Bookmark",
        primaryjoin="Bookmark.post_id == Post.id",
        foreign_keys="Bookmark.post_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    likes = relationship(
        "Like",
        primaryjoin="Like.post_id == Post.id",
        foreign_keys="Like.post_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PostMedia(Base):
    __tablename__ = "post_media"
    __table_args__ = (
        PrimaryKeyConstraint("post_id", "id", name="pk_post_media"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        PrimaryKeyConstraint("post_id", "id", name="pk_comments"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    post = relationship(
        "Post",
        primaryjoin="Comment.post_id == Post.id",
        foreign_keys="Comment.post_id",
        lazy="selectin",
        overlaps="comments",
    )
    author = relationship("User", lazy="selectin")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "id", name="pk_bookmarks"),
        UniqueConstraint("user_id", "post_id", name="uq_user_post_bookmark"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    post = relationship(
        "Post",
        primaryjoin="Bookmark.post_id == Post.id",
        foreign_keys="Bookmark.post_id",
        lazy="selectin",
        overlaps="bookmarks",
    )


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        PrimaryKeyConstraint("post_id", "id", name="pk_likes"),
        UniqueConstraint("user_id", "post_id", name="uq_user_post_like"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    post = relationship(
        "Post",
        primaryjoin="Like.post_id == Post.id",
        foreign_keys="Like.post_id",
        lazy="selectin",
        overlaps="likes",
    )
