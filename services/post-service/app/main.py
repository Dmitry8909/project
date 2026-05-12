from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from shared.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from shared.database import create_engine, create_session_factory
from shared.database import Base
from shared.citus_setup import setup_citus_distribution
from shared.timeline import TimelineClient
from shared.hot_cache import HotCache
from shared.kafka_client import KafkaClient
from shared.scylla import ScyllaClient
from app.routers import posts, feed
import asyncio
import logging

logger = logging.getLogger("post-service")
settings = get_settings()


async def try_start_scylla():
    try:
        loop = asyncio.get_event_loop()
        client = ScyllaClient(settings.scylla_contact_points, settings.scylla_keyspace)
        await loop.run_in_executor(None, client.start)
        return client
    except Exception as e:
        logger.warning(f"ScyllaDB unavailable (non-fatal): {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception:
            logger.warning("Table creation race (another worker already created them)")

    citus_dsn = settings.database_url.replace("pgbouncer", "citus-coordinator")
    try:
        citus_engine = create_async_engine(
            citus_dsn, isolation_level="AUTOCOMMIT",
        )
        async with citus_engine.connect() as conn:
            await setup_citus_distribution(
                conn,
                workers=["citus-worker-1", "citus-worker-2"],
            )
        await citus_engine.dispose()
    except Exception as e:
        logger.warning(f"Citus setup skipped: {e}")

    app.state.engine = engine
    app.state.db_factory = create_session_factory(engine)

    use_cluster = settings.redis_timeline_cluster

    app.state.timeline = None
    app.state.hot_cache = None
    app.state.kafka = None
    app.state.scylla = None

    try:
        timeline = TimelineClient(settings.redis_timeline_url, use_cluster=use_cluster)
        await timeline.start()
        app.state.timeline = timeline
    except Exception as e:
        logger.warning(f"Redis timeline unavailable: {e}")

    try:
        hot_cache = HotCache(settings.redis_timeline_url, use_cluster=use_cluster)
        await hot_cache.start()
        app.state.hot_cache = hot_cache
    except Exception as e:
        logger.warning(f"Hot cache unavailable: {e}")

    try:
        kafka = KafkaClient(settings.kafka_bootstrap_servers)
        await kafka.start()
        app.state.kafka = kafka
    except Exception as e:
        logger.warning(f"Kafka unavailable: {e}")

    try:
        scylla = await try_start_scylla()
        app.state.scylla = scylla
    except Exception as e:
        logger.warning(f"ScyllaDB unavailable (non-fatal): {e}")

    yield

    await engine.dispose()
    if app.state.timeline:
        await app.state.timeline.close()
    if app.state.hot_cache:
        await app.state.hot_cache.close()
    if app.state.kafka:
        await app.state.kafka.close()
    if app.state.scylla:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, app.state.scylla.close)


app = FastAPI(title="Post Service", lifespan=lifespan)

app.include_router(posts.router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(feed.router, prefix="/api/v1/feed", tags=["feed"])


@app.get("/health")
async def health():
    return {"status": "ok"}
