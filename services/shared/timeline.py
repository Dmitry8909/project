import json
import redis.asyncio as aioredis


class TimelineClient:
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

    async def push_to_timeline(self, user_id: str, post_id: str, score: float):
        await self.start()
        key = f"timeline:{user_id}"
        await self._redis.zadd(key, {post_id: score})
        await self._redis.expire(key, 604800)

    async def get_timeline(self, user_id: str, start: int = 0, stop: int = 19):
        await self.start()
        key = f"timeline:{user_id}"
        return await self._redis.zrevrange(key, start, stop)

    async def remove_from_timeline(self, user_id: str, post_id: str):
        await self.start()
        key = f"timeline:{user_id}"
        await self._redis.zrem(key, post_id)

    async def get_fanout_followers_count(self, user_id: str) -> int | None:
        await self.start()
        key = f"fanout:followers:{user_id}"
        val = await self._redis.get(key)
        if val is not None:
            return int(val)
        return None

    async def set_fanout_followers_count(self, user_id: str, count: int, ttl: int = 3600):
        await self.start()
        key = f"fanout:followers:{user_id}"
        await self._redis.setex(key, ttl, count)

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
