import json
import logging
import uuid
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

registry = CollectorRegistry(auto_describe=True)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "path", "status_code"],
    registry=registry,
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "path"],
    registry=registry,
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": getattr(record, "service", "unknown"),
            "request_id": getattr(record, "request_id", None),
            "path": getattr(record, "path", None),
            "method": getattr(record, "method", None),
            "status_code": getattr(record, "status_code", None),
        }
        return json.dumps(payload, default=str)


def configure_logging(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


def setup_observability(app: FastAPI, service_name: str) -> logging.Logger:
    logger = configure_logging(service_name)

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = perf_counter()

        logger.info(
            "request_started",
            extra={
                "service": service_name,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )

        response = None
        try:
            response = await call_next(request)
        except Exception as exc:
            duration = perf_counter() - start_time
            logger.exception(
                "request_failed",
                extra={
                    "service": service_name,
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": 500,
                },
            )
            REQUEST_COUNT.labels(service_name, request.method, request.url.path, "500").inc()
            REQUEST_DURATION.labels(service_name, request.method, request.url.path).observe(duration)
            raise exc

        duration = perf_counter() - start_time
        status_code = getattr(response, "status_code", 500)
        response.headers["x-request-id"] = request_id

        logger.info(
            "request_completed",
            extra={
                "service": service_name,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
            },
        )

        REQUEST_COUNT.labels(service_name, request.method, request.url.path, str(status_code)).inc()
        REQUEST_DURATION.labels(service_name, request.method, request.url.path).observe(duration)
        return response

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    return logger
