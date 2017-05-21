import aioamqp
import asyncio
import umsgpack as msgpack
import inspect
from functools import wraps
from .task import Task
from .response import Response
from .logger import logger

class Queue(object):
    def __init__(self, host='localhost', port=None, ssl=False):
        self.host = host
        self.port = port if port is not None else 5671 if ssl else 5672
        self.ssl = ssl
        self._handlers = {}
        self._protocol = None

    async def _connect(self, retry, **kwargs):
        if retry is not False:
            while self._protocol is None:
                try:
                    transport, self._protocol = await aioamqp.connect(host=self.host, port=self.port, ssl=self.ssl, **kwargs)
                except:
                    logger.warn(f'Could not connect to amqp://{self.host}:{self.port}/. Trying again in {retry} second(s).')
                    await asyncio.sleep(retry)
        else:
            transport, self._protocol = await aioamqp.connect(host=self.host, port=self.port, ssl=self.ssl, **kwargs)

        logger.info(f'Connected to amqp://{self.host}:{self.port}/.')

    @staticmethod
    def _make_consumer(task_name, handler):
        async def consumer(channel, body, envelope, properties):
            corr_id = properties.correlation_id
            response = Response(channel, envelope, properties)
            try:
                data = msgpack.unpackb(body)
                logger.info(f'Received request for {task_name} ({corr_id})')
            except Exception as err:
                logger.error(f'Could not unpack message: {err} ({corr_id})')
                await response.send(err, None)
                return

            try:
                if inspect.iscoroutinefunction(handler):
                    result = await handler(data)
                else:
                    result = handler(data)
            except Exception as err:
                logger.error(f'Exception while executing {task_name}: {err} ({corr_id})')
                await response.send(err, None)
                return

            await response.send(None, result)
        return consumer

    async def create(self, task_name, data, no_response=False):
        channel = await self._protocol.channel()
        task = Task(task_name, data, channel, no_response=no_response)
        await task.send()
        return task

    async def _connect_and_init(self, retry=5, **kwargs):
        await self._connect(retry=retry, **kwargs)
        for (queue, (handler, options)) in self._handlers.items():
            channel = await self._protocol.channel()
            await channel.queue_declare(queue_name=queue, **options['queue'])
            await channel.basic_qos(**options['qos'])
            await channel.basic_consume(self._make_consumer(queue, handler), queue_name=queue)
            logger.info(f'Consuming on queue {queue}.')

    def start(self, retry=5, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._connect_and_init(retry=retry **kwargs))
        try:
            loop.run_forever()
        finally:
            loop.close()

    def on(self, queue, durable=True, prefetch_count=1, prefetch_size=0, connection_global=False):
        def decorator(f):
            @wraps(f)
            def wrapper(data):
                return f(data)
            options = {
                'queue': {
                    'durable': durable
                },
                'qos': {
                    'prefetch_count': prefetch_count,
                    'prefetch_size': prefetch_size,
                    'connection_global': connection_global
                }
            }
            self._handlers[queue] = (wrapper, options)
            return wrapper
        return decorator