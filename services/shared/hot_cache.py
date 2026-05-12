import json
import redis.asyncio as aioredis


class HotCache:
    def __init__(self, redis_url: str, use_cluster: bool = False):
        self._redis: aioredis.Redis | None = None
        self._redis_url = redis_url
        self._use_cluster = use_cluster

    async def start(self):
        if self._redis is not None:
            return
        if self._use_cluster:
            from redis.asyncio.cluster import RedisCluster
            from redis.cluster import ClusterNode
            nodes = []
            for part in self._redis_url.split(","):
                part = part.strip()
                if part.startswith("redis://"):
                    part = part[len("redis://"):]
                if ":" in part:
                    host, port = part.rsplit(":", 1)
                    nodes.append(ClusterNode(host, int(port)))
                else:
                    nodes.append(ClusterNode(part, 6379))
            self._redis = RedisCluster(
                startup_nodes=nodes,
                decode_responses=True,
            )
        else:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )

    async def get_post(self, post_id: str) -> dict | None:
        await self.start()
        data = await self._redis.get(f"hot:post:{post_id}")
        if data:
            return json.loads(data)
        return None

    async def set_post(self, post_id: str, post_data: dict, ttl: int = 300):
        await self.start()
        await self._redis.setex(
            f"hot:post:{post_id}",
            ttl,
            json.dumps(post_data, default=str),
        )

    async def invalidate_post(self, post_id: str):
        await self.start()
        await self._redis.delete(f"hot:post:{post_id}")

    async def is_hot(self, post_id: str) -> bool:
        await self.start()
        return await self._redis.exists(f"hot:post:{post_id}") > 0

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
