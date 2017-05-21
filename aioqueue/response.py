import umsgpack as msgpack
from .logger import logger

class Response(object):
    def __init__(self, channel, envelope, properties):
        self.channel = channel
        self.envelope = envelope
        self.properties = properties

    async def send(self, exception, result):
        routing_key = self.properties.reply_to
        correlation_id = self.properties.correlation_id
        delivery_tag = self.envelope.delivery_tag

        payload = msgpack.packb((str(exception) if exception is not None else None, result))

        logger.info(f'Sending response to queue {routing_key} ({correlation_id})')
        await self.channel.basic_publish(
            payload=payload,
            exchange_name='',
            routing_key=routing_key,
            properties={
                'correlation_id': correlation_id
            }
        )

        await self.channel.basic_client_ack(delivery_tag=delivery_tag)