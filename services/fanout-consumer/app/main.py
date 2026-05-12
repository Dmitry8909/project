import asyncio
import json
import os
import logging
from datetime import datetime, timezone

from shared.config import get_settings
from shared.timeline import TimelineClient
from shared.scylla import ScyllaClient

logger = logging.getLogger("fanout-consumer")
settings = get_settings()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://blog:blog_pass@localhost:5432/blog",
)
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_TIMELINE_URL = os.getenv("REDIS_TIMELINE_URL", "redis://localhost:6380/0")
REDIS_TIMELINE_CLUSTER = os.getenv("REDIS_TIMELINE_CLUSTER", "false").lower() == "true"
SCYLLA_CONTACT_POINTS = os.getenv("SCYLLA_CONTACT_POINTS", "localhost")
CELEBRITY_THRESHOLD = settings.celebrity_follower_threshold


async def get_db_pool():
    import asyncpg
    dsn = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    for attempt in range(30):
        try:
            return await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        except Exception as e:
            if attempt == 29:
                raise
            logger.warning(f"DB not ready (attempt {attempt + 1}/30): {e}")
            await asyncio.sleep(2)


async def get_follower_ids(pool, author_id: str) -> list[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT follower_id FROM subscriptions WHERE following_id = $1",
            author_id,
        )
        return [str(r["follower_id"]) for r in rows]


async def get_follower_count(pool, author_id: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM subscriptions WHERE following_id = $1",
            author_id,
        )
        return row["cnt"] if row else 0


async def process_post_created(
    loop: asyncio.AbstractEventLoop,
    pool,
    timeline: TimelineClient,
    scylla: ScyllaClient | None,
    data: dict,
):
    post_id = data["post_id"]
    author_id = data["author_id"]
    timestamp = data.get("timestamp", datetime.now(tz=timezone.utc).timestamp())

    follower_count = await get_follower_count(pool, author_id)
    is_celebrity = follower_count >= CELEBRITY_THRESHOLD

    if is_celebrity:
        await timeline.set_fanout_followers_count(author_id, follower_count)
        return

    follower_ids = await get_follower_ids(pool, author_id)

    batch_size = 1000
    for i in range(0, len(follower_ids), batch_size):
        batch = follower_ids[i:i + batch_size]
        for fid in batch:
            await timeline.push_to_timeline(fid, post_id, timestamp)
            if scylla:
                await loop.run_in_executor(
                    None, scylla.insert_feed_entry, fid, post_id, author_id, timestamp,
                )


async def try_start_timeline():
    for attempt in range(30):
        try:
            client = TimelineClient(REDIS_TIMELINE_URL, use_cluster=REDIS_TIMELINE_CLUSTER)
            await client.start()
            return client
        except Exception as e:
            if attempt == 29:
                raise
            logger.warning(f"Redis not ready (attempt {attempt + 1}/30): {e}")
            await asyncio.sleep(2)


async def try_start_scylla():
    try:
        loop = asyncio.get_event_loop()
        client = ScyllaClient(SCYLLA_CONTACT_POINTS, settings.scylla_keyspace)
        await loop.run_in_executor(None, client.start)
        return client
    except Exception as e:
        logger.warning(f"ScyllaDB unavailable (non-fatal): {e}")
        return None


async def try_start_kafka_consumer():
    from aiokafka import AIOKafkaConsumer
    for attempt in range(30):
        try:
            consumer = AIOKafkaConsumer(
                "fanout",
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="fanout-consumer",
                value_deserializer=lambda v: json.loads(v.decode()),
                enable_auto_commit=True,
                auto_offset_reset="latest",
                request_timeout_ms=30000,
                session_timeout_ms=30000,
            )
            await consumer.start()
            return consumer
        except Exception as e:
            if attempt == 29:
                raise
            logger.warning(f"Kafka not ready (attempt {attempt + 1}/30): {e}")
            await asyncio.sleep(2)


async def consume():
    loop = asyncio.get_event_loop()
    pool = await get_db_pool()
    logger.info("Connected to PostgreSQL")

    timeline = await try_start_timeline()
    logger.info("Connected to Redis timeline")

    scylla = await try_start_scylla()

    consumer = await try_start_kafka_consumer()
    logger.info("Connected to Kafka, waiting for messages...")

    try:
        async for msg in consumer:
            data = msg.value
            event_type = data.get("type")
            if event_type == "post.created":
                await process_post_created(loop, pool, timeline, scylla, data)
    except asyncio.CancelledError:
        pass
    finally:
        await consumer.stop()
        await timeline.close()
        if scylla:
            await loop.run_in_executor(None, scylla.close)
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consume())
