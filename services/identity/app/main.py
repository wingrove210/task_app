import smtplib
from email.message import EmailMessage
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis import Redis
from sqlalchemy.orm import Session

from .core.config import Settings
from .core.database import SessionLocal, User, initialize

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Identity Service")
security_scheme = HTTPBearer(auto_error=False)
redis_client = Redis.from_url(Settings.REDIS_URL, decode_responses=True)

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_SECONDS = 120


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_rate_limit_key(endpoint: str, identifier: str) -> str:
    return f"rate_limit:{endpoint}:{identifier}"


def enforce_rate_limit(request: Request, endpoint: str) -> None:
    remote_addr = request.client.host if request.client else "unknown"
    key = get_rate_limit_key(endpoint, remote_addr)
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)

    if count > RATE_LIMIT_MAX:
        ttl = redis_client.ttl(key)
        retry_seconds = ttl if ttl and ttl > 0 else RATE_LIMIT_WINDOW_SECONDS
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Try again in {retry_seconds} seconds.",
        )


@app.on_event("startup")
def startup_event() -> None:
    initialize()
    with SessionLocal() as db:
        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin_user:
            admin_user = User(
                email="admin@example.com",
                username="admin",
                full_name="Administrator",
                hashed_password=pwd_context.hash("admin123"),
                role="admin",
            )
            db.add(admin_user)
        else:
            admin_user.username = admin_user.username or "admin"
            admin_user.full_name = admin_user.full_name or "Administrator"
            admin_user.role = admin_user.role or "admin"
            if not admin_user.hashed_password:
                admin_user.hashed_password = pwd_context.hash("admin123")

        db.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "identity"}


def send_welcome_email(email: str, username: str) -> bool:
    if not Settings.SMTP_HOST or not Settings.SMTP_PORT:
        print("SMTP is not configured. Welcome email was not sent.")
        return False

    message = EmailMessage()
    message["Subject"] = f"Welcome to {Settings.APP_NAME}"
    message["From"] = f"{Settings.SMTP_FROM_NAME} <{Settings.SMTP_FROM_EMAIL}>"
    message["To"] = email
    message.set_content(
        f"Hello {username}!\n\n"
        f"Your account has been created successfully in {Settings.APP_NAME}.\n"
        f"We will send important updates to this address: {email}."
    )

    try:
        with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT, timeout=5) as server:
            if Settings.SMTP_USE_TLS:
                server.starttls()
            if Settings.SMTP_USERNAME:
                server.login(Settings.SMTP_USERNAME, Settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as exc:  # pragma: no cover - best effort delivery
        print(f"Failed to send welcome email to {email}: {exc}")
        return False


@app.post("/auth/register", response_model=dict)
def register(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    full_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "register")
    normalized_email = email.strip().lower()
    normalized_username = username.strip().lower()

    if not normalized_email or not normalized_username or not password:
        raise HTTPException(status_code=400, detail="Email, username and password are required")

    if "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address")

    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=409, detail="A user with this email address is already registered")

    if db.query(User).filter(User.username == normalized_username).first():
        raise HTTPException(status_code=409, detail="A user with this username is already registered")

    user = User(
        email=normalized_email,
        username=normalized_username,
        full_name=full_name.strip() if full_name else "",
        hashed_password=pwd_context.hash(password),
        role="member",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    email_sent = send_welcome_email(user.email, user.username)

    token = create_access_token(user)
    message = f"Registration successful. A welcome email was sent to {user.email}."
    if not email_sent:
        message = (
            "Registration successful, but the welcome email could not be sent because SMTP is not configured. "
            "Set SMTP_HOST/SMTP_PORT (or run MailHog locally) to deliver emails."
        )
    elif Settings.SMTP_HOST == "mailhog":
        message = (
            f"Registration successful. A welcome email was sent to {user.email}. "
            "View it in MailHog at http://127.0.0.1:8025."
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "message": message,
    }


@app.post("/auth/login", response_model=dict)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, "login")
    candidate = username.strip().lower()
    if not candidate:
        raise HTTPException(status_code=400, detail="Username is required")

    user = db.query(User).filter(User.username == candidate).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with this username was not found. Please register first.",
        )

    if not pwd_context.verify(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="The password is incorrect")

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
    }


def get_current_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header is required")

    try:
        payload = jwt.decode(credentials.credentials, Settings.JWT_SECRET, algorithms=[Settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    return {"user_id": user.id, "email": user.email, "role": user.role}


@app.get("/admin/users", response_model=list[dict])
def list_all_users(
    current_admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
        }
        for user in users
    ]


@app.delete("/admin/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    current_admin: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    if current_admin["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"message": f"User {user_id} deleted successfully"}


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
