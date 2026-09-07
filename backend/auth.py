"""Authentication for resource-intensive analysis routes."""

import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ANALYSIS_API_KEY_ENV = "ANALYSIS_API_KEY"
MINIMUM_API_KEY_LENGTH = 32

_bearer = HTTPBearer(auto_error=False)


def require_analysis_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
) -> None:
    """Require a configured bearer token and compare it in constant time."""
    configured_key = os.getenv(ANALYSIS_API_KEY_ENV, "")
    if len(configured_key) < MINIMUM_API_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis authentication is not configured",
        )

    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode("utf-8"),
        configured_key.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
