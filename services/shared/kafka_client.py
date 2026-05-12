import json
from aiokafka import AIOKafkaProducer


class KafkaClient:
    def __init__(self, bootstrap_servers: str):
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode(),
            )
            await self._producer.start()

    async def publish(self, topic: str, key: str, value: dict):
        await self.start()
        await self._producer.send(
            topic=topic,
            key=key.encode(),
            value=value,
        )

    async def close(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
