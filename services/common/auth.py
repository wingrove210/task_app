"""
Common authentication module for microservices.
Provides centralized authentication validation.
"""
from typing import Optional

import httpx

from .exceptions import AuthenticationError


def get_current_user(
    identity_service_url: str,
    authorization: Optional[str] = None,
) -> dict:
    """
    Validate user token with identity service.

    Args:
        identity_service_url: URL of identity service
        authorization: Authorization header with Bearer token

    Returns:
        User data from identity service

    Raises:
        AuthenticationError: If token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]

    try:
        response = httpx.post(
            f"{identity_service_url}/internal/validate",
            json={"token": token},
            timeout=3.0,
        )

        if response.status_code != 200:
            raise AuthenticationError("Invalid or expired token")

        user_data = response.json()
        if not user_data.get("user_id"):
            raise AuthenticationError("Invalid token: missing user ID")

        return user_data

    except httpx.RequestError as exc:
        raise AuthenticationError("Failed to validate token") from exc
