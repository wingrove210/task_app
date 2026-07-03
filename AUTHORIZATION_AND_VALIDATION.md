# Authorization & Data Validation System

## Overview

Система авторизации и валидации данных была полностью переработана для удобства разработки и поддержки микросервисной архитектуры.

### Ключевые особенности

1. **Централизованная авторизация** - одна функция для всех микросервисов
2. **Типобезопасность** - валидация через Pydantic с подробными ошибками
3. **Единообразная обработка ошибок** - стандартные HTTP исключения
4. **Сохранена архитектура** - микросервисная структура не изменена

## Структура

```
services/
├── common/                           # Общий модуль для всех сервисов
│   ├── auth.py                      # Авторизация (JWT валидация)
│   ├── exceptions.py                # Стандартные исключения
│   ├── events.py                    # Публикация событий
│   ├── models.py                    # Pydantic модели для валидации
│   └── README.md                    # Документация
├── project/app/main.py              # Использует common.*
├── task/app/main.py                 # Использует common.*
└── identity/                         # Сервис аутентификации
```

## Авторизация

### Для разработчика микросервиса

```python
from fastapi import Depends, FastAPI, Header
from typing import Optional
from common.auth import get_current_user

app = FastAPI()

# Wrapper для dependency injection
def get_current_user_dep(authorization: Optional[str] = Header(None)):
    return get_current_user(IDENTITY_SERVICE_URL, authorization)

# Использование в endpoint
@app.post("/projects")
def create_project(
    data: ProjectCreateRequest,
    current_user: dict = Depends(get_current_user_dep),
):
    owner_id = current_user["user_id"]  # Данные пользователя
    ...
```

### Как работает

1. Клиент отправляет запрос с header: `Authorization: Bearer <token>`
2. Микросервис вызывает `get_current_user()`
3. Функция отправляет запрос на identity service для валидации
4. Возвращаются данные пользователя: `{"user_id": 1, "email": "user@example.com", ...}`
5. Если токен невалиден, выбрасывается `AuthenticationError` (401)

## Валидация данных

### Создание проекта

```python
from common.models import ProjectCreateRequest

@app.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    data: ProjectCreateRequest,  # Автоматическая валидация!
    db: Session = Depends(get_db),
):
    # data.name - строка, 1-255 символов
    # data.description - опциональный, макс 2000 символов
```

**Валидация:**
- `name` обязательно, 1-255 символов
- `description` опционально, макс 2000 символов

**Пример запроса:**
```json
{
    "name": "Мобильное приложение",
    "description": "Разработка iOS и Android приложения"
}
```

### Создание задачи

```python
from common.models import TaskCreateRequest, TaskStatus, TaskPriority

@app.post("/projects/{project_id}/tasks")
def create_task(
    project_id: int,
    data: TaskCreateRequest,  # Автоматическая валидация!
):
    # data.title - 1-500 символов
    # data.description - опционально, макс 5000 символов
    # data.status - "todo", "in_progress", "done"
    # data.priority - "low", "medium", "high", "urgent"
    # data.assignee_id - опциональный ID пользователя
```

**Пример запроса:**
```json
{
    "title": "Реализовать аутентификацию",
    "description": "Добавить JWT-based аутентификацию",
    "status": "in_progress",
    "priority": "high",
    "assignee_id": 1
}
```

## Обработка ошибок

### Автоматические ошибки валидации

При неправильных данных Pydantic автоматически возвращает 422:

```json
{
    "detail": [
        {
            "loc": ["body", "name"],
            "msg": "ensure this value has at most 255 characters",
            "type": "value_error.string.max_length"
        }
    ]
}
```

### Пользовательские исключения

```python
from common.exceptions import (
    AuthenticationError,     # 401 - Токен невалиден
    AuthorizationError,      # 403 - Недостаточно прав
    NotFoundError,           # 404 - Ресурс не найден
    ValidationError,         # 422 - Ошибка валидации
    ConflictError,          # 409 - Конфликт
)

# Использование
if not project:
    raise NotFoundError("Project")

if current_user["id"] != project.owner_id:
    raise AuthorizationError("Only owner can edit project")
```

## События

### Публикация событий

```python
from common.events import publish_event

@app.post("/projects")
def create_project(data: ProjectCreateRequest, ...):
    project = create_in_db(data)
    
    # Отправить событие другим сервисам
    publish_event(
        rabbitmq_host=Settings.RABBITMQ_HOST,
        routing_key="project.created",
        payload={
            "project_id": project.id,
            "owner_id": project.owner_id,
            "name": project.name,
        }
    )
```

## API примеры

### Создание проекта

```bash
curl -X POST http://localhost:8001/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Новый проект",
    "description": "Описание проекта"
  }'
```

**Ответ (201 Created):**
```json
{
    "id": 1,
    "name": "Новый проект",
    "description": "Описание проекта",
    "owner_id": 1
}
```

### Создание задачи

```bash
curl -X POST http://localhost:8002/projects/1/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Сделать редизайн",
    "description": "Обновить интерфейс",
    "status": "in_progress",
    "priority": "high",
    "assignee_id": 2
  }'
```

**Ответ (201 Created):**
```json
{
    "id": 5,
    "title": "Сделать редизайн",
    "description": "Обновить интерфейс",
    "status": "in_progress",
    "priority": "high",
    "project_id": 1,
    "creator_id": 1,
    "assignee_id": 2,
    "tags": [],
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
}
```

## Коды ошибок

| Код | Ошибка | Пример |
|-----|--------|--------|
| 401 | AuthenticationError | Невалиден токен |
| 403 | AuthorizationError | Нет доступа |
| 404 | NotFoundError | Проект не найден |
| 409 | ConflictError | Уже существует |
| 422 | ValidationError | Неправильные данные |

## Тестирование с токеном

1. Получить токен от сервиса аутентификации:
```bash
curl -X POST http://localhost:8003/token \
  -H "Content-Type: application/json" \
  -d '{"email": "user", "password": "user"}'
```

2. Использовать токен в запросах:
```bash
curl -X GET http://localhost:8001/projects \
  -H "Authorization: Bearer <token_from_step_1>"
```

## Миграция существующего кода

### Перед (старый способ)

```python
@app.post("/projects")
def create_project(payload: dict, current_user=Depends(get_current_user)):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    # ... создание проекта
```

### После (новый способ)

```python
@app.post("/projects")
def create_project(
    data: ProjectCreateRequest,  # Валидация встроена!
    current_user: dict = Depends(get_current_user_dep),
):
    # name уже валидирован и типобезопасен
    # ... создание проекта
```

## Преимущества

✅ **Меньше кода** - нет повторяющейся валидации
✅ **Лучше документация** - OpenAPI/Swagger автоматически
✅ **Типобезопасность** - IDE помогает при разработке
✅ **Единообразная авторизация** - одна функция везде
✅ **Проще отладка** - понятные сообщения об ошибках
✅ **Масштабируемость** - легко добавлять новые сервисы

## Документация компонентов

- [common/README.md](./services/common/README.md) - Подробная документация модулей
