"""
Common event publishing module for domain events.
"""
import json
from typing import Any

import pika

from .exceptions import ValidationError


def publish_event(
    rabbitmq_host: str,
    routing_key: str,
    payload: dict[str, Any],
) -> bool:
    """
    Publish a domain event to RabbitMQ.

    Args:
        rabbitmq_host: RabbitMQ host address
        routing_key: Event routing key (e.g., 'project.created')
        payload: Event payload dictionary

    Returns:
        True if successful, False otherwise
    """
    if not routing_key or not payload:
        raise ValidationError("routing_key and payload are required")

    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitmq_host, heartbeat=30)
        )
        channel = connection.channel()
        channel.exchange_declare(
            exchange="domain-events", exchange_type="topic", durable=True
        )
        channel.basic_publish(
            exchange="domain-events",
            routing_key=routing_key,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
        return True
    except Exception:
        return False
