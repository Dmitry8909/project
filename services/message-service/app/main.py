import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
from shared.database import create_engine, create_session_factory
from shared.database import Base
from shared.citus_setup import setup_citus_distribution
from app.routers import messages


logger = logging.getLogger("message-service")
settings = get_settings()


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
    yield
    await engine.dispose()


app = FastAPI(title="Message Service", lifespan=lifespan)

app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])


@app.get("/health")
async def health():
    return {"status": "ok"}
