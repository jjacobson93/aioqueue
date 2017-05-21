# aioqueue
A Python Task Queue library using RabbitMQ (aioamqp) and asyncio

## Install
```bash
pip install aioqueue
```

## Create a queue
```python
from aioqueue import Queue
q = Queue() # connects to rmqp://localhost:5671 by default

# on start-up, wait 10 seconds after each failure to connect (defaults to 5)
q = Queue(retry=10)

# start up the queue
q.start() # runs the connection in an asyncio event loop

# or if you need to start the queue asynchronously
await q.start_async()
```

## Define a task
```python
# defines a queue named 'my_task' when `start()` is called
@q.on('my_task')
def my_task(data):
    message = data['message']
    print(message)
    return 'world'
```

## Trigger a task
```python
t = await q.task('my_task', { 'message': 'hello' })
```

## Get the result of a task
```python
result = await t.result()
```
Note: A call to `result()` isn't necessary if you don't want the result of the task. You can also pass `no_response=True` to `q.create()` if you really don't want the result and don't want the queue waiting around for a result. In that case, a call to `result()` will always return `None`.

## Close a queue
```python
await q.close()
```

## Using `async with`
```python
async with Queue() as q:
    t = await q.task('my_task', { 'message': 'Go' })
    result = await t.result()
```

## Sending raw bytes
When creating a task with `task()`, the data gets packed with `msgpack`. To prevent this and just send raw bytes, use the keyword argument `raw=True`. If you're passing bytes that are not `msgpack` data and using the `on()` decorator, pass `raw=True` to `on()` as well

```python
@q.on('raw_task', raw=True)
async def raw_task(data):
    # data is raw bytes
    print(data)

await q.task('my_task', b'Hello', raw=True)
```

## License
MIT