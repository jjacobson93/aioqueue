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
await q.start()
```

## Define a task
```python
# defines a queue named 'my task' when `start()` is called
@q.on('my task')
def my_task(data):
    message = data['message']
    print(message)
    return 'world'
```

## Trigger a task
```python
t = await q.create('my task', { 'message': 'hello' })
```

## Get the result of a task
```python
result = await t.result()
```
Note: A call to `result()` isn't necessary if you don't want the result of the task. You can also pass `no_response=True` to `q.create()` if you really don't want the result and don't want the queue waiting around for a result. In that case, a call to `result()` will always return `None`.

## License
MIT