# Task Manager API

This repository now follows a cleaner microservice-oriented layout with explicit service boundaries, shared infrastructure, and a more maintainable structure for future growth.

## Services

- Identity service: authentication, registration, and JWT validation on port 8001
- Project service: project CRUD and ownership rules on port 8002
- Task service: task CRUD and project-level task access on port 8003

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

The service code is now organized around a small shared bootstrap layer under services/common, with each service keeping its own config and database wiring under its app/core package.
See [docs/architecture.md](docs/architecture.md) for a short overview.

