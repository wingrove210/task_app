import json
import logging
from typing import Any, Optional

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self) -> None:
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisError as exc:
            logger.warning("Redis unavailable: %s", exc)
            return False

    def get(self, key: str) -> Optional[str]:
        try:
            return self.client.get(key)
        except RedisError as exc:
            logger.warning("Redis get failed for %s: %s", key, exc)
            return None

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        try:
            if ttl_seconds:
                self.client.setex(key, ttl_seconds, value)
            else:
                self.client.set(key, value)
            return True
        except RedisError as exc:
            logger.warning("Redis set failed for %s: %s", key, exc)
            return False

    def get_json(self, key: str) -> Optional[Any]:
        value = self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        return self.set(key, json.dumps(value), ttl_seconds)

    def delete(self, key: str) -> bool:
        try:
            self.client.delete(key)
            return True
        except RedisError as exc:
            logger.warning("Redis delete failed for %s: %s", key, exc)
            return False
