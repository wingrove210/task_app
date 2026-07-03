# Task Manager API

This repository now uses a microservice-first architecture only. The legacy monolithic application layer has been removed, and the system is composed of three focused services.

## Services

- Identity service: authentication, registration, and JWT validation on port 8001
- Project service: project creation and ownership rules on port 8002
- Task service: task creation and project-scoped task access on port 8003

## Local development

```bash
cp .env.example .env
make up
```

The stack includes:
- Identity service: http://localhost:8001/health
- Project service: http://localhost:8002/health
- Task service: http://localhost:8003/health
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- RabbitMQ UI: http://localhost:15672

## Useful commands

```bash
make down
make logs
make test
```

## Architecture notes

Each service owns its own domain logic and persistence model in its own app package, while shared bootstrap concerns live in services/common.
See [docs/architecture.md](docs/architecture.md) for a short overview.

