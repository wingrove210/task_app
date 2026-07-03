# Common Microservices Module

Shared utilities and models for the task-manager microservices.

## Overview

This module provides common functionality used across project and task microservices:

- **Authentication**: Centralized token validation with identity service
- **Exception Handling**: Standardized HTTP exceptions for consistency
- **Event Publishing**: Domain event publishing through RabbitMQ
- **Data Validation**: Pydantic models for request/response validation

## Modules

### `auth.py`
Handles authentication validation using JWT tokens.

```python
from common.auth import get_current_user

# Extract and validate token from request
user_data = get_current_user(
    identity_service_url="http://identity:8000",
    authorization="Bearer <token>"
)
# Returns: {"user_id": 1, "email": "user@example.com", ...}
```

**Key Functions:**
- `get_current_user()` - Validates JWT token with identity service
- `extract_token_from_header()` - Parses Authorization header

### `exceptions.py`
Custom exception classes for consistent error handling.

```python
from common.exceptions import (
    AuthenticationError,  # 401 Unauthorized
    AuthorizationError,   # 403 Forbidden
    NotFoundError,        # 404 Not Found
    ValidationError,      # 422 Unprocessable Entity
    ConflictError,        # 409 Conflict
)
```

### `events.py`
Domain event publishing through RabbitMQ.

```python
from common.events import publish_event

success = publish_event(
    rabbitmq_host="rabbitmq",
    routing_key="project.created",
    payload={"project_id": 1, "name": "My Project"}
)
```

### `models.py`
Pydantic models for request/response validation.

**Request Models:**
- `ProjectCreateRequest` - Project creation with validation
- `ProjectUpdateRequest` - Project update data
- `TaskCreateRequest` - Task creation with validation
- `TaskUpdateRequest` - Task update data

**Response Models:**
- `ProjectResponse` - Project response format
- `TaskResponse` - Task response format

**Enums:**
- `TaskStatus` - todo, in_progress, done
- `TaskPriority` - low, medium, high, urgent

## Usage Examples

### Using Authentication in Microservices

```python
from fastapi import Depends, FastAPI, Header
from typing import Optional
from common.auth import get_current_user
from common.exceptions import AuthenticationError

app = FastAPI()

def get_current_user_dep(authorization: Optional[str] = Header(None)):
    """Dependency for endpoints requiring authentication."""
    return get_current_user(IDENTITY_SERVICE_URL, authorization)

@app.post("/projects")
def create_project(
    data: ProjectCreateRequest,
    current_user: dict = Depends(get_current_user_dep),
):
    # current_user contains validated user data
    project_owner = current_user["user_id"]
    ...
```

### Using Validated Models

```python
from common.models import ProjectCreateRequest, TaskCreateRequest

# Request with validation
@app.post("/projects")
def create_project(data: ProjectCreateRequest):
    # data.name is validated: 1-255 characters
    # data.description is optional, max 2000 characters
    # Invalid requests return 422 with validation errors
    ...

# Example valid request:
# {
#     "name": "Mobile App",
#     "description": "Development of mobile application for iOS and Android"
# }
```

### Publishing Domain Events

```python
from common.events import publish_event

@app.post("/projects")
def create_project(...):
    project = db.add_and_commit(...)
    
    # Publish event for other services
    publish_event(
        rabbitmq_host=Settings.RABBITMQ_HOST,
        routing_key="project.created",
        payload={
            "project_id": project.id,
            "owner_id": project.owner_id,
            "name": project.name,
        }
    )
    ...
```

## Benefits

1. **Centralized Authentication**: Single source of truth for auth validation
2. **Type Safety**: Pydantic models ensure data integrity
3. **Consistent Error Handling**: Standardized HTTP exceptions across services
4. **Code Reusability**: No duplication between microservices
5. **Easy Maintenance**: Changes propagate to all services automatically

## Microservice Integration

Both `project` and `task` services use these common utilities:

```
services/
├── common/              # ← This module
│   ├── auth.py
│   ├── exceptions.py
│   ├── events.py
│   └── models.py
├── project/app/main.py  # Uses common.auth, common.models, common.events
├── task/app/main.py     # Uses common.auth, common.models, common.events
└── identity/            # Authentication service
```

## Error Responses

All services now return consistent error responses:

```json
// 401 Unauthorized
{"detail": "Missing or invalid authorization header"}

// 403 Forbidden  
{"detail": "Insufficient permissions"}

// 404 Not Found
{"detail": "Project not found"}

// 422 Validation Error
{"detail": "Project name cannot be empty"}

// 409 Conflict
{"detail": "Resource already exists"}
```

## Future Enhancements

- [ ] Rate limiting middleware
- [ ] Request logging
- [ ] Metrics collection
- [ ] Distributed tracing

