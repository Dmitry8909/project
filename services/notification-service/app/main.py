import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from shared.config import get_settings
from shared.database import Base, create_engine, create_session_factory
from shared.models import Notification
from shared.rabbitmq import RabbitMQClient
from app.routers import notifications

settings = get_settings()
db_factory = None
redis_pubsub = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, data: dict):
        if user_id in self.active_connections:
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass


manager = ConnectionManager()


def _notification_title(data: dict) -> str:
    t = data.get("type", "")
    actor = data.get("actor_name", "Someone")
    if t == "like":
        return f"{actor} liked your post"
    elif t == "follow":
        return f"{actor} started following you"
    elif t == "new_message":
        return f"New message from {actor}"
    elif t == "new_post":
        return f"{actor} created a new post"
    elif t == "comment_mention":
        return f"{actor} mentioned you in a comment"
    return "New notification"


async def handle_notification(data: dict):
    user_id = data.get("user_id")
    if not user_id:
        return

    if data.get("type") not in ("new_message", "read_receipt"):
        try:
            async with db_factory() as db:
                reference = data.get("post_id") or data.get("message_id")
                notif_content = data.get("content_preview") or data.get("actor_name", "")
                notification = Notification(
                    user_id=user_id,
                    type=data.get("type", "general"),
                    title=_notification_title(data),
                    content=notif_content,
                    reference_id=reference,
                )
                db.add(notification)
                await db.commit()
        except Exception:
            pass

    try:
        await redis_pubsub.publish("notifications:ws", json.dumps(data))
    except Exception:
        pass


async def redis_ws_subscriber():
    import redis.asyncio as aioredis

    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        async with r.pubsub() as pubsub:
            await pubsub.subscribe("notifications:ws")
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    user_id = data.get("user_id")
                    if user_id:
                        await manager.send_to_user(user_id, data)
                except Exception:
                    pass
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Redis subscriber error: {e}")


async def consume_notifications():
    global db_factory
    try:
        rmq = RabbitMQClient(settings.rabbitmq_url)
        await rmq.connect()

        exchange_name = "notifications"
        channel = rmq._channel
        exchange = await channel.declare_exchange(exchange_name, type="direct", durable=True)

        queue = await channel.declare_queue("notification.all", durable=True)
        await queue.bind(exchange, routing_key="new_post")
        await queue.bind(exchange, routing_key="new_message")
        await queue.bind(exchange, routing_key="follow")
        await queue.bind(exchange, routing_key="like")
        await queue.bind(exchange, routing_key="comment_mention")
        await queue.bind(exchange, routing_key="read_receipt")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    await handle_notification(data)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Notification consumer error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_factory, redis_pubsub

    import redis.asyncio as aioredis

    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        pass
    db_factory = create_session_factory(engine)
    app.state.db_factory = db_factory

    redis_pubsub = aioredis.from_url(settings.redis_url, decode_responses=True)

    tasks = [
        asyncio.create_task(consume_notifications()),
        asyncio.create_task(redis_ws_subscriber()),
    ]
    yield
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await engine.dispose()
    await redis_pubsub.close()


app = FastAPI(title="Notification Service", lifespan=lifespan)

app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@app.get("/health")
async def health():
    return {"status": "ok"}
