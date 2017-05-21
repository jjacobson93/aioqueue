import asyncio
import umsgpack as msgpack
from .exceptions import RemoteException
from uuid import uuid4
from .logger import logger

class Task(object):
    def __init__(self, name, data, channel, no_response=False, raw=False):
        self.id = str(uuid4())
        self.name = name
        self.data = data
        self.raw = raw
        self.no_response = no_response
        self._channel = channel
        self._waiter = asyncio.Event()
        self._callback_queue = None
        self._response = None

    async def send(self):
        if not self.no_response:
            self._callback_queue = await self._make_callback_queue()

        payload = msgpack.packb(self.data) if not self.raw else self.data

        logger.info(f'Ensuring queue `{self.name}` exists.')
        await self._channel.queue_declare(self.name, durable=True)

        logger.info(f'Publishing to `{self.name}`: {self.id}')
        await self._channel.basic_publish(
            payload=payload,
            exchange_name='',
            routing_key=self.name,
            properties={
                'correlation_id': self.id,
                'reply_to': self._callback_queue,
                'delivery_mode': 2
            },
        )

        logger.info(f'Published {self.id} to `{self.name}`')

    async def retry(self):
        self._waiter = asyncio.Event()
        self._response = None
        await self.send()

    async def result(self, timeout=None):
        if self.no_response:
            return

        if timeout is not None:
            logger.info(f'Waiting for response to {self.id} with {timeout} second timeout')
        else:
            logger.info(f'Waiting for response to {self.id} with no timeout')

        # this is silly
        await asyncio.wait_for(self._waiter.wait(), timeout)

        try:
            exc, result = msgpack.unpackb(self._response)
        except Exception as err:
            logger.error(f'Could not unpack response: {err}')
            return None

        if exc is not None:
            raise RemoteException(exc)
        return result

    async def _make_callback_queue(self):
        result = await self._channel.queue_declare(queue_name='', exclusive=True)
        callback_queue = result['queue']
        logger.info(f'Created callback queue: {callback_queue}')

        await self._channel.basic_consume(
            self._on_response,
            no_ack=True,
            queue_name=callback_queue,
        )
        return callback_queue

    async def _on_response(self, channel, body, envelope, properties):
        if self.id == properties.correlation_id:
            self._response = body
            logger.info(f'Received response for {self.id}')

        logger.debug(f'Setting the waiter for {self.id}')
        self._waiter.set()

        # remove callback queue
        logger.info(f'Deleting callback queue `{self._callback_queue}` for {self.id}')
        await channel.queue_delete(self._callback_queue, no_wait=True)