import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from shared.config import get_settings
from shared.database import create_engine, create_session_factory
from shared.database import Base
from shared.citus_setup import setup_citus_distribution
from app.routers import auth, users, subscriptions


logger = logging.getLogger("user-service")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception:
            logger.warning("Table creation race (another worker already created them)")
        try:
            await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS receive_like_notifications BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS receive_follow_notifications BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS receive_new_message_notifications BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS receive_comment_mention_notifications BOOLEAN DEFAULT TRUE
            """))
        except Exception:
            pass

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
        logger.warning(f"Citus setup skipped (will retry on next restart): {e}")

    app.state.engine = engine
    app.state.db_factory = create_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(title="User Service", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    return JSONResponse(
        status_code=422,
        content={"detail": first["msg"]},
    )


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])


@app.get("/health")
async def health():
    return {"status": "ok"}
