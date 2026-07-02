import json
import logging
from typing import Any, Optional

import pika
from pika.exceptions import AMQPError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self) -> None:
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def _connect(self) -> bool:
        if self._channel is not None:
            return True

        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD,
            )
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                virtual_host=settings.RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=30,
                blocked_connection_timeout=30,
            )
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(exchange="domain-events", exchange_type="topic", durable=True)
            return True
        except AMQPError as exc:
            logger.warning("RabbitMQ unavailable: %s", exc)
            return False

    def publish(self, routing_key: str, payload: dict[str, Any]) -> bool:
        if not self._connect():
            return False

        try:
            assert self._channel is not None
            self._channel.basic_publish(
                exchange="domain-events",
                routing_key=routing_key,
                body=json.dumps(payload).encode("utf-8"),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
            )
            return True
        except AMQPError as exc:
            logger.warning("RabbitMQ publish failed for %s: %s", routing_key, exc)
            return False

    def healthcheck(self) -> bool:
        return self._connect()
