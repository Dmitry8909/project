import os
from fastapi import APIRouter, Request, Response
from httpx import AsyncClient, HTTPError

router = APIRouter()

SERVICE_MAP = {
    "auth": "USER_SERVICE_URL",
    "users": "USER_SERVICE_URL",
    "subscriptions": "USER_SERVICE_URL",
    "posts": "POST_SERVICE_URL",
    "feed": "POST_SERVICE_URL",
    "messages": "MESSAGE_SERVICE_URL",
    "media": "MEDIA_SERVICE_URL",
    "notifications": "NOTIFICATION_SERVICE_URL",
}

DEFAULT_URLS = {
    "USER_SERVICE_URL": "http://user-service:8001",
    "POST_SERVICE_URL": "http://post-service:8002",
    "MESSAGE_SERVICE_URL": "http://message-service:8003",
    "MEDIA_SERVICE_URL": "http://media-service:8004",
    "NOTIFICATION_SERVICE_URL": "http://notification-service:8005",
}

client = AsyncClient(timeout=120.0)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_request(request: Request, path: str):
    parts = path.strip("/").split("/")
    service_key = parts[0] if parts else ""
    sub_path = "/".join(parts[1:]) if len(parts) > 1 else ""

    if service_key not in SERVICE_MAP:
        return Response(
            content='{"detail": "Service not found"}',
            status_code=404,
            media_type="application/json",
        )

    env_var = SERVICE_MAP[service_key]
    base_url = os.getenv(env_var, DEFAULT_URLS[env_var])
    target_url = f"{base_url}/api/v1/{service_key}"
    if sub_path:
        target_url += f"/{sub_path}"

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
            params=request.query_params,
        )
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type", "application/json"),
        )
    except HTTPError:
        return Response(
            content='{"detail": "Service unavailable"}',
            status_code=502,
            media_type="application/json",
        )
