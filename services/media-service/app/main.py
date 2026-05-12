from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.minio_client import get_minio_client, ensure_bucket
from app.routers import upload


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    mc = get_minio_client(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    ensure_bucket(mc, settings.minio_bucket)
    app.state.minio_client = mc
    yield


app = FastAPI(title="Media Service", lifespan=lifespan)

app.include_router(upload.router, prefix="/api/v1/media", tags=["media"])


@app.get("/health")
async def health():
    return {"status": "ok"}
