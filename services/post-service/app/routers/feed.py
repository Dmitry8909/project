from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.models import Post, Subscription
from shared.scylla import ScyllaClient
from app.deps import get_db, get_current_user_id
from app.routers.posts import PostResponse, post_to_response

router = APIRouter()

CELEBRITY_THRESHOLD = 10000


@router.get("", response_model=list[PostResponse])
async def get_feed(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    timeline = getattr(request.app.state, "timeline", None) if request else None
    hot_cache = getattr(request.app.state, "hot_cache", None) if request else None
    scylla: ScyllaClient | None = getattr(request.app.state, "scylla", None) if request else None

    post_ids: list[str] = []
    celebrity_ids: list[str] = []

    if timeline and skip == 0:
        post_ids = await timeline.get_timeline(user_id, 0, limit * 2 - 1)

    if post_ids:
        all_post_ids = post_ids[skip:skip + limit]
        result = []
        for pid in all_post_ids:
            if hot_cache:
                cached = await hot_cache.get_post(pid)
                if cached:
                    result.append(PostResponse(**cached))
                    continue

            row = await db.execute(
                select(Post).where(Post.id == pid)
                .options(
                    selectinload(Post.media),
                    selectinload(Post.author),
                    selectinload(Post.comments),
                    selectinload(Post.bookmarks),
                    selectinload(Post.likes),
                )
            )
            post = row.scalar_one_or_none()
            if post:
                resp = await post_to_response(post, user_id, db)
                if hot_cache:
                    await hot_cache.set_post(str(pid), resp.model_dump())
                result.append(resp)
        return result

    # Если нет в Redis — пробуем ScyllaDB (warm storage)
    if scylla and skip == 0:
        import asyncio
        loop = asyncio.get_event_loop()
        scylla_posts = await loop.run_in_executor(
            None, scylla.get_feed, user_id, limit,
        )
        if scylla_posts:
            result = []
            for entry in scylla_posts:
                pid = entry["post_id"]
                if hot_cache:
                    cached = await hot_cache.get_post(pid)
                    if cached:
                        result.append(PostResponse(**cached))
                        continue

                row = await db.execute(
                    select(Post).where(Post.id == pid)
                    .options(selectinload(Post.media), selectinload(Post.author),
                             selectinload(Post.comments), selectinload(Post.bookmarks),
                             selectinload(Post.likes))
                )
                post = row.scalar_one_or_none()
                if post:
                    resp = await post_to_response(post, user_id, db)
                    if hot_cache:
                        await hot_cache.set_post(str(pid), resp.model_dump())
                    result.append(resp)
            if result:
                return result

    following_ids = await db.execute(
        select(Subscription.following_id).where(Subscription.follower_id == user_id)
    )
    following = [str(row[0]) for row in following_ids.all()]
    following.append(user_id)

    for fid in list(following):
        if timeline:
            count = await timeline.get_fanout_followers_count(fid)
            if count is not None and count >= CELEBRITY_THRESHOLD:
                celebrity_ids.append(fid)
                following.remove(fid)

    sql_posts = []

    if following:
        result = await db.execute(
            select(Post)
            .where(Post.author_id.in_(following))
            .options(
                selectinload(Post.media),
                selectinload(Post.author),
                selectinload(Post.comments),
                selectinload(Post.bookmarks),
                selectinload(Post.likes),
            )
            .order_by(Post.created_at.desc())
            .offset(skip).limit(limit)
        )
        sql_posts.extend(result.scalars().all())

    if celebrity_ids:
        celeb_result = await db.execute(
            select(Post)
            .where(Post.author_id.in_(celebrity_ids))
            .options(
                selectinload(Post.media),
                selectinload(Post.author),
                selectinload(Post.comments),
                selectinload(Post.bookmarks),
                selectinload(Post.likes),
            )
            .order_by(Post.created_at.desc())
            .offset(skip).limit(limit)
        )
        sql_posts.extend(celeb_result.scalars().all())

    sql_posts.sort(key=lambda p: p.created_at, reverse=True)
    sql_posts = sql_posts[skip:skip + limit]

    result = []
    for p in sql_posts:
        resp = await post_to_response(p, user_id, db)
        if hot_cache:
            await hot_cache.set_post(str(p.id), resp.model_dump())
        result.append(resp)
    return result
