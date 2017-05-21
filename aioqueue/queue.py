import aioamqp
import asyncio
import umsgpack as msgpack
import inspect
import signal
import functools
from .task import Task
from .response import Response
from .logger import logger

class Queue(object):
    def __init__(self, host='localhost', port=None, ssl=False, log_level=None, retry=5, **connect_kwargs):
        self.host = host
        self.port = port if port is not None else 5671 if ssl else 5672
        self.ssl = ssl
        self._handlers = {}
        self._transport = None
        self._protocol = None
        self.retry = retry
        self._connect_kwargs = connect_kwargs

        if log_level is not None:
            logger.setLevel(log_level)

    async def connect(self):
        if self.retry is not False:
            while self._protocol is None:
                try:
                    self._transport, self._protocol = await aioamqp.connect(host=self.host, port=self.port, ssl=self.ssl, **self._connect_kwargs)
                except:
                    logger.warn(f'Could not connect to amqp://{self.host}:{self.port}/. Trying again in {self.retry} second(s).')
                    await asyncio.sleep(self.retry)
        else:
            self._transport, self._protocol = await aioamqp.connect(host=self.host, port=self.port, ssl=self.ssl, **self._connect_kwargs)

        logger.info(f'Connected to amqp://{self.host}:{self.port}/.')

    @staticmethod
    def _make_consumer(task_name, handler, raw=False):
        async def consumer(channel, body, envelope, properties):
            corr_id = properties.correlation_id
            response = Response(channel, envelope, properties)

            try:
                data = msgpack.unpackb(body) if not raw else body
                logger.info(f'Received request for {task_name} ({corr_id})')
                logger.debug(f'[{corr_id}][\'data\'] = {data}')
            except Exception as err:
                logger.error(f'Could not unpack message: {err} ({corr_id})')
                await response.send(err, None)
                return

            try:
                if inspect.iscoroutinefunction(handler):
                    logger.debug(f'Calling coroutine {handler} ({corr_id})')
                    result = await handler(data)
                    logger.debug(f'Coroutine {handler} returned with {result} ({corr_id})')
                else:
                    logger.debug(f'Calling function {handler} ({corr_id})')
                    result = handler(data)
                    logger.debug(f'Function {handler} returned with {result} ({corr_id})')
            except Exception as err:
                logger.error(f'Exception while executing {task_name}: {err} ({corr_id})')
                await response.send(err, None)
                return

            await response.send(None, result)
        return consumer

    async def task(self, task_name, data, no_response=False, raw=False):
        channel = await self._protocol.channel()
        task = Task(task_name, data, channel, no_response=no_response, raw=raw)
        await task.send()
        return task

    async def start_async(self):
        await self.connect()
        for (queue, (handler, options)) in self._handlers.items():
            channel = await self._protocol.channel()
            await channel.queue_declare(queue_name=queue, **options['queue'])
            await channel.basic_qos(**options['qos'])
            await channel.basic_consume(self._make_consumer(queue, handler, **options['handler']), queue_name=queue)
            logger.info(f'Consuming on queue {queue}.')

    def start(self):
        loop = asyncio.get_event_loop()

        for signame in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(getattr(signal, signame), loop.stop)

        loop.run_until_complete(self.start_async())
        try:
            loop.run_forever()
        finally:
            loop.close()

    async def close(self):
        await self._protocol.close()
        self._transport.close()

    def on(self, queue, raw=False, durable=True, prefetch_count=1, prefetch_size=0, connection_global=False):
        def decorator(func):
            options = {
                'queue': {
                    'durable': durable
                },
                'qos': {
                    'prefetch_count': prefetch_count,
                    'prefetch_size': prefetch_size,
                    'connection_global': connection_global
                },
                'handler': {
                    'raw': raw
                }
            }
            self._handlers[queue] = (func, options)
            return func
        return decorator

    async def __aenter__(self):
        await self.start_async()

    async def __aexit__(self):
        await self.close()