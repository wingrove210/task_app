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

## SMTP / email delivery

For real external email delivery, set these values in `.env` before running the stack:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=no-reply@taskmanager.example.com
SMTP_FROM_NAME="Task Manager"
```

If you want to continue using local development email capture, use MailHog:

```bash
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
```

Then start the app normally:

```bash
make up
```

Real delivery works because the identity service reads SMTP settings from environment variables and uses them when sending the welcome email.

## Architecture notes

The service code is now organized around a small shared bootstrap layer under services/common, with each service keeping its own config and database wiring under its app/core package.
See [docs/architecture.md](docs/architecture.md) for a short overview.

