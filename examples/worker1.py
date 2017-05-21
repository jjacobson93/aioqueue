import asyncio
import logging
from aioqueue import Queue

q = Queue(host='rabbitmq', log_level=logging.DEBUG)

@q.on('my_task')
async def my_task(message):
    print(f'Received message: {message}')
    await asyncio.sleep(10)
    return f'Hello, {message}'

@q.on('will_timeout')
async def will_timeout(msg):
    print(f'Message: {msg}')
    await asyncio.sleep(15)
    return 'never will see this'

if __name__ == '__main__':
    q.start()