from fastapi import HTTPException

from app.models.user import UserRole


def require_admin(user):
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user