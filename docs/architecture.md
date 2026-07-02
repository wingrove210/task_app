# Architecture overview

The project is organized as a small microservice platform with clear service boundaries:

- Identity service: authentication, JWT issuing, and token validation.
- Project service: project lifecycle and ownership rules.
- Task service: task lifecycle and project-level task access.

Shared infrastructure is intentionally isolated in the services layer:

- PostgreSQL for persistence
- Redis for lightweight cache hints
- RabbitMQ for domain-event publication

Each service exposes a health endpoint and is built from a small dependency stack so it remains easy to evolve.
