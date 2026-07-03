from fastapi import Header, HTTPException, Request, Depends
import httpx
from .core.config import Settings

async def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="token required")
    token = authorization.split(" ", 1)[1]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{Settings.IDENTITY_SERVICE_URL}/internal/validate",
            json={"token": token},
            timeout=3.0,
        )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="invalid token")
    return response.json()
