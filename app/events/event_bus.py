import logging
from typing import Optional

from app.events.domain_events import DomainEvent
from app.integrations.rabbitmq import RabbitMQPublisher

logger = logging.getLogger(__name__)


class DomainEventBus:
    def __init__(self, publisher: Optional[RabbitMQPublisher] = None) -> None:
        self.publisher = publisher or RabbitMQPublisher()

    def publish(self, event: DomainEvent) -> bool:
        payload = event.to_payload()
        payload["event_type"] = event.__class__.__name__
        published = self.publisher.publish(event.event_name, payload)
        if not published:
            logger.info("Domain event published to local fallback: %s", event.event_name)
        return published


_event_bus: Optional[DomainEventBus] = None


def get_event_bus() -> DomainEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = DomainEventBus()
    return _event_bus
