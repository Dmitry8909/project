import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from pydantic import BaseModel
from minio import Minio
from shared.config import get_settings
from app.deps import get_minio, get_current_user_id

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


class UploadResponse(BaseModel):
    file_id: str
    file_url: str
    file_type: str


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    mc: Minio = Depends(get_minio),
    user_id: str = Depends(get_current_user_id),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    file_ext = ALLOWED_CONTENT_TYPES[file.content_type]
    file_id = str(uuid.uuid4())
    object_name = f"{user_id}/{file_id}.{file_ext}"

    settings = get_settings()
    mc.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        data=io.BytesIO(content),
        length=len(content),
        content_type=file.content_type,
    )

    file_url = f"/api/v1/media/{object_name}"

    return UploadResponse(
        file_id=file_id,
        file_url=file_url,
        file_type=file.content_type,
    )


@router.get("/{user_id}/{object_name}")
async def get_file(
    user_id: str,
    object_name: str,
    mc: Minio = Depends(get_minio),
    current_user_id: str = Depends(get_current_user_id),
):
    settings = get_settings()
    full_path = f"{user_id}/{object_name}"
    try:
        response = mc.get_object(
            bucket_name=settings.minio_bucket,
            object_name=full_path,
        )
        content = response.read()
        response.close()
        response.release_conn()
        content_type = response.getheader("Content-Type", "application/octet-stream")
        return Response(content=content, media_type=content_type)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )


@router.get("/{legacy_name}")
async def get_file_legacy(
    legacy_name: str,
    mc: Minio = Depends(get_minio),
    current_user_id: str = Depends(get_current_user_id),
):
    settings = get_settings()
    try:
        response = mc.get_object(
            bucket_name=settings.minio_bucket,
            object_name=legacy_name,
        )
        content = response.read()
        response.close()
        response.release_conn()
        content_type = response.getheader("Content-Type", "application/octet-stream")
        return Response(content=content, media_type=content_type)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
