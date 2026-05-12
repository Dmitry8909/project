import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.models import Post, PostMedia, Comment, Bookmark, Like, User, Subscription
from shared.rabbitmq import RabbitMQClient
from shared.config import get_settings
from app.deps import get_db, get_current_user_id

router = APIRouter()


class MediaItem(BaseModel):
    file_url: str
    file_type: str


class CreatePostRequest(BaseModel):
    content: str
    media: list[MediaItem] = []


class PostMediaResponse(BaseModel):
    id: str
    file_url: str
    file_type: str
    order: int


class PostResponse(BaseModel):
    id: str
    author_id: str
    author_name: str
    author_avatar: str | None
    content: str
    media: list[PostMediaResponse] = []
    comments_count: int = 0
    likes_count: int = 0
    bookmarks_count: int = 0
    reposts_count: int = 0
    is_liked: bool = False
    is_bookmarked: bool = False
    created_at: str
    updated_at: str


class CreateCommentRequest(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_id: str
    author_name: str
    author_username: str
    author_avatar: str | None
    content: str
    created_at: str


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    req: CreatePostRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    if not req.content.strip() and not req.media:
        raise HTTPException(status_code=400, detail="Content or media required")

    post = Post(author_id=user_id, content=req.content)
    db.add(post)
    await db.flush()

    for i, m in enumerate(req.media):
        pm = PostMedia(post_id=post.id, file_url=m.file_url, file_type=m.file_type, order=i)
        db.add(pm)

    await db.commit()
    await db.refresh(post)

    timestamp = datetime.now(tz=timezone.utc).timestamp()

    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        settings = get_settings()

        followers = await db.execute(
            select(Subscription.follower_id).where(Subscription.following_id == user_id)
        )
        follower_ids = [row[0] for row in followers.all()]

        if follower_ids:
            user_prefs = await db.execute(
                select(User.id).where(
                    User.id.in_(follower_ids),
                    User.receive_new_post_notifications == True,
                )
            )
            allowed_ids = {str(row[0]) for row in user_prefs.all()}

            rmq = RabbitMQClient(settings.rabbitmq_url)
            for fid in follower_ids:
                if str(fid) in allowed_ids:
                    await rmq.publish("notifications", "new_post", {
                        "type": "new_post",
                        "user_id": str(fid),
                        "actor_name": user.display_name or user.username if user else "Unknown",
                        "post_id": str(post.id),
                    })
            await rmq.close()
    except Exception:
        pass

    try:
        kafka = request.app.state.kafka if hasattr(request.app.state, "kafka") else None
        if kafka:
            await kafka.publish("fanout", str(user_id), {
                "type": "post.created",
                "post_id": str(post.id),
                "author_id": str(user_id),
                "timestamp": timestamp,
            })
    except Exception:
        pass

    try:
        hot_cache = request.app.state.hot_cache if hasattr(request.app.state, "hot_cache") else None
        if hot_cache:
            post_resp = await post_to_response(post, user_id, db)
            await hot_cache.set_post(str(post.id), post_resp.model_dump())
    except Exception:
        pass

    return await post_to_response(post, user_id, db)


@router.get("/my", response_model=list[PostResponse])
async def get_my_posts(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(Post)
        .where(Post.author_id == user_id)
        .options(selectinload(Post.media), selectinload(Post.author),
                 selectinload(Post.comments), selectinload(Post.bookmarks),
                 selectinload(Post.likes))
        .order_by(Post.created_at.desc())
        .offset(skip).limit(limit)
    )
    return [await post_to_response(p, user_id, db) for p in result.scalars().all()]


@router.get("/user/{author_id}", response_model=list[PostResponse])
async def get_user_posts(
    author_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(Post)
        .where(Post.author_id == author_id, Post.repost_of_id == None)
        .options(selectinload(Post.media), selectinload(Post.author),
                 selectinload(Post.comments), selectinload(Post.bookmarks),
                 selectinload(Post.likes))
        .order_by(Post.created_at.desc())
        .offset(skip).limit(limit)
    )
    return [await post_to_response(p, user_id, db) for p in result.scalars().all()]


@router.get("/bookmarks/all", response_model=list[PostResponse])
async def get_bookmarks(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    result = await db.execute(
        select(Post).join(Bookmark).where(Bookmark.user_id == user_id)
        .options(selectinload(Post.media), selectinload(Post.author),
                 selectinload(Post.comments), selectinload(Post.bookmarks),
                 selectinload(Post.likes))
        .order_by(Bookmark.created_at.desc())
        .offset(skip).limit(limit)
    )
    return [await post_to_response(p, user_id, db) for p in result.scalars().all()]


@router.get("/liked", response_model=list[PostResponse])
async def get_liked_posts(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    author_id: str = Query(default=None, description="User whose liked posts to fetch"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    target_id = author_id or user_id
    is_own = target_id == user_id

    if not is_own:
        result = await db.execute(select(User).where(User.id == target_id))
        target_user = result.scalar_one_or_none()
        if not target_user or not target_user.likes_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user's likes are private",
            )

    result = await db.execute(
        select(Post)
        .join(Like, Like.post_id == Post.id)
        .where(Like.user_id == target_id)
        .options(selectinload(Post.media), selectinload(Post.author),
                 selectinload(Post.comments), selectinload(Post.bookmarks),
                 selectinload(Post.likes))
        .order_by(Like.created_at.desc())
        .offset(skip).limit(limit)
    )
    return [await post_to_response(p, user_id, db) for p in result.scalars().all()]


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Post).where(Post.id == post_id)
        .options(selectinload(Post.media), selectinload(Post.author),
                 selectinload(Post.comments), selectinload(Post.bookmarks),
                 selectinload(Post.likes))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return await post_to_response(post, user_id, db)


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Post).where(Post.id == post_id, Post.author_id == user_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found or not authorized")
    await db.delete(post)
    await db.commit()
    return {"detail": "Post deleted"}


@router.post("/{post_id}/comment", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: str,
    req: CreateCommentRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    post = await db.execute(select(Post).where(Post.id == post_id))
    if not post.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Post not found")

    comment = Comment(post_id=post_id, author_id=user_id, content=req.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    result = await db.execute(select(User).where(User.id == user_id))
    author = result.scalar_one_or_none()
    author_name = author.display_name or author.username if author else "Unknown"

    try:
        mentions = re.findall(r"@(\w+)", req.content)
        if mentions:
            settings = get_settings()
            rmq = RabbitMQClient(settings.rabbitmq_url)
            for username in mentions:
                user_result = await db.execute(
                    select(User).where(User.username == username)
                )
                mentioned = user_result.scalar_one_or_none()
                if mentioned and str(mentioned.id) != user_id and mentioned.receive_comment_mention_notifications:
                    await rmq.publish("notifications", "comment_mention", {
                        "type": "comment_mention",
                        "user_id": str(mentioned.id),
                        "actor_name": author_name,
                        "post_id": str(comment.post_id),
                        "content_preview": req.content[:100],
                    })
            await rmq.close()
    except Exception:
        pass

    return CommentResponse(
        id=str(comment.id),
        post_id=str(comment.post_id),
        author_id=str(comment.author_id),
        author_name=author.display_name or author.username if author else "Unknown",
        author_username=author.username if author else "Unknown",
        author_avatar=author.avatar_url if author else None,
        content=comment.content,
        created_at=comment.created_at.isoformat(),
    )


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
async def get_comments(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await db.execute(
        select(Comment).where(Comment.post_id == post_id)
        .options(selectinload(Comment.author))
        .order_by(Comment.created_at.asc())
        .offset(skip).limit(limit)
    )
    comments = result.scalars().all()
    return [
        CommentResponse(
            id=str(c.id),
            post_id=str(c.post_id),
            author_id=str(c.author_id),
            author_name=c.author.display_name or c.author.username,
            author_username=c.author.username,
            author_avatar=c.author.avatar_url,
            content=c.content,
            created_at=c.created_at.isoformat(),
        )
        for c in comments
    ]


@router.post("/{post_id}/repost", status_code=201)
async def repost(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    original = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.author))
    )
    original_post = original.scalar_one_or_none()
    if not original_post:
        raise HTTPException(status_code=404, detail="Post not found")

    repost = Post(
        author_id=user_id,
        content=original_post.content,
        repost_of_id=post_id,
    )
    db.add(repost)
    await db.commit()
    return {"detail": "Reposted", "post_id": str(repost.id)}


@router.post("/{post_id}/bookmark")
async def toggle_bookmark(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    post = await db.execute(select(Post).where(Post.id == post_id))
    if not post.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Post not found")

    existing = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == user_id, Bookmark.post_id == post_id
        )
    )
    if existing.scalar_one_or_none():
        await db.execute(
            delete(Bookmark).where(
                Bookmark.user_id == user_id, Bookmark.post_id == post_id
            )
        )
        await db.commit()
        return {"bookmarked": False}
    else:
        bm = Bookmark(user_id=user_id, post_id=post_id)
        db.add(bm)
        await db.commit()
        return {"bookmarked": True}

@router.post("/{post_id}/like")
async def toggle_like(
    post_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.author))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing = await db.execute(
        select(Like).where(Like.user_id == user_id, Like.post_id == post_id)
    )
    if existing.scalar_one_or_none():
        await db.execute(
            delete(Like).where(Like.user_id == user_id, Like.post_id == post_id)
        )
        await db.commit()
        hot_cache = getattr(request.app.state, "hot_cache", None) if request else None
        if hot_cache:
            await hot_cache.invalidate_post(post_id)
        return {"liked": False}
    else:
        like = Like(user_id=user_id, post_id=post_id)
        db.add(like)
        await db.commit()

        if str(post.author_id) != user_id:
            try:
                author_pref = await db.execute(
                    select(User.receive_like_notifications).where(User.id == post.author_id)
                )
                if author_pref.scalar_one_or_none():
                    result = await db.execute(select(User).where(User.id == user_id))
                    actor = result.scalar_one_or_none()
                    settings = get_settings()
                    rmq = RabbitMQClient(settings.rabbitmq_url)
                    await rmq.publish("notifications", "like", {
                        "type": "like",
                        "user_id": str(post.author_id),
                        "actor_id": user_id,
                        "actor_name": actor.display_name or actor.username if actor else "Unknown",
                        "post_id": post_id,
                    })
                    await rmq.close()
            except Exception:
                pass

        hot_cache = getattr(request.app.state, "hot_cache", None) if request else None
        if hot_cache:
            await hot_cache.invalidate_post(post_id)

        return {"liked": True}


async def post_to_response(post: Post, current_user_id: str, db: AsyncSession) -> PostResponse:
    author_name = post.author.display_name or post.author.username if post.author else "Unknown"
    is_bm = any(str(b.user_id) == current_user_id for b in (post.bookmarks or []))
    is_liked = any(str(l.user_id) == current_user_id for l in (post.likes or []))
    return PostResponse(
        id=str(post.id),
        author_id=str(post.author_id),
        author_name=author_name,
        author_avatar=post.author.avatar_url if post.author else None,
        content=post.content,
        media=[
            PostMediaResponse(id=str(m.id), file_url=m.file_url, file_type=m.file_type, order=m.order)
            for m in (post.media or [])
        ],
        comments_count=len(post.comments or []),
        likes_count=len(post.likes or []),
        bookmarks_count=len(post.bookmarks or []),
        reposts_count=0,
        is_liked=is_liked,
        is_bookmarked=is_bm,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
    )
