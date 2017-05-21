import asyncio
import logging
from aioqueue import Queue

q = Queue(host='rabbitmq', log_level=logging.DEBUG)

async def my_task():
    t = await q.task('my_task', 'world')
    result = await t.result()
    print(f'Result of `my_task`: {result}')

async def will_timeout():
    t = await q.task('will_timeout', 'foo')
    try:
        result = await t.result(timeout=2) # 2 second timeout
        print(f'Should never see this result: {result}')
    except asyncio.TimeoutError:
        print(f'Timed out waiting for result. As expected.')

async def main():
    await q.connect()
    await asyncio.wait([
        my_task(),
        will_timeout()
    ])
    await q.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
