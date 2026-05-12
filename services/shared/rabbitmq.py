import json
import asyncio
from typing import Callable, Awaitable
from aio_pika import connect_robust, Message, IncomingMessage, ExchangeType
from aio_pika.abc import AbstractRobustConnection, AbstractChannel, AbstractQueue


class RabbitMQClient:
    _connection: AbstractRobustConnection | None = None
    _channel: AbstractChannel | None = None

    def __init__(self, url: str):
        self._url = url
        self._consumers: dict[str, asyncio.Task] = {}

    async def connect(self):
        if self._connection is None or self._connection.is_closed:
            self._connection = await connect_robust(self._url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

    async def close(self):
        for task in self._consumers.values():
            task.cancel()
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def publish(self, exchange_name: str, routing_key: str, data: dict):
        await self.connect()
        exchange = await self._channel.declare_exchange(
            exchange_name, ExchangeType.DIRECT, durable=True
        )
        message = Message(
            body=json.dumps(data, default=str).encode(),
            delivery_mode=2,
        )
        await exchange.publish(message, routing_key=routing_key)

    async def consume(
        self,
        exchange_name: str,
        routing_key: str,
        queue_name: str,
        callback: Callable[[dict], Awaitable[None]],
    ):
        await self.connect()
        exchange = await self._channel.declare_exchange(
            exchange_name, ExchangeType.DIRECT, durable=True
        )
        queue: AbstractQueue = await self._channel.declare_queue(
            queue_name, durable=True
        )
        await queue.bind(exchange, routing_key=routing_key)

        async def on_message(message: IncomingMessage):
            async with message.process():
                data = json.loads(message.body.decode())
                await callback(data)

        await queue.consume(on_message)
