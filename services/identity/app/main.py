from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .core.config import Settings
from .core.database import SessionLocal, User, initialize
from .schemas import RegisterRequest, LoginRequest

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Identity Service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event() -> None:
    initialize()
    with SessionLocal() as db:
        if not db.query(User).filter(User.email == "admin@example.com").first():
            db.add(
                User(
                    email="admin@example.com",
                    full_name="Administrator",
                    hashed_password=pwd_context.hash("admin123"),
                    role="admin",
                )
            )
            db.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "identity"}


@app.post("/auth/register", response_model=dict)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.get("email")
    password = payload.get("password")
    full_name = payload.get("full_name", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="email already registered")

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=pwd_context.hash(password),
        role="member",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=dict)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.get("email")
    password = payload.get("password")

    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/internal/validate", response_model=dict)
def validate_token(payload: dict):
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="token required")

    try:
        decoded = jwt.decode(token, Settings.JWT_SECRET, algorithms=[Settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid token")

    return {"user_id": int(user_id), "email": decoded.get("email", ""), "role": decoded.get("role", "member")}


def create_access_token(user: User) -> str:
    payload = {"sub": str(user.id), "email": user.email, "role": user.role}
    return jwt.encode(payload, Settings.JWT_SECRET, algorithm=Settings.JWT_ALGORITHM)
