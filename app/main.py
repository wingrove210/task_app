from fastapi import FastAPI

from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.comments import router as comments_router
from app.api.tags import router as tags_router
from app.api import auth, users
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import get_password_hash

app = FastAPI()


@app.on_event("startup")
def create_default_users():
    with SessionLocal() as db:
        defaults = [
            {
                "email": "admin",
                "full_name": "Administrator",
                "password": "admin",
                "role": "admin",
            },
            {
                "email": "user",
                "full_name": "Regular User",
                "password": "user",
                "role": "member",
            },
            {
                "email": "guest",
                "full_name": "Guest User",
                "password": "guest",
                "role": "member",
            },
        ]

        for data in defaults:
            user = db.query(User).filter(User.email == data["email"]).first()
            if not user:
                user = User(
                    email=data["email"],
                    full_name=data["full_name"],
                    hashed_password=get_password_hash(data["password"]),
                    is_active=True,
                    role=data["role"],
                )
                db.add(user)
        db.commit()


app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(comments_router)
app.include_router(tags_router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}
