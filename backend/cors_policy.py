"""Explicit cross-origin policy for the browser frontend."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_DEVELOPMENT_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://frontend:3000",
)


@dataclass(frozen=True)
class CorsPolicy:
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls, source: Mapping[str, str] | None = None) -> "CorsPolicy":
        values = os.environ if source is None else source
        configured = values.get("CORS_ALLOWED_ORIGINS")
        if configured is not None:
            origins = _parse_origins(configured)
        elif values.get("ENVIRONMENT", "").casefold() == "production":
            origins = ()
        else:
            origins = _DEVELOPMENT_ORIGINS
        return cls(allowed_origins=origins)


def install_cors(app: FastAPI, policy: CorsPolicy) -> None:
    """Install CORS only when explicitly permitted origins exist."""
    if not policy.allowed_origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(policy.allowed_origins),
        allow_credentials=False,
        allow_methods=["POST"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _parse_origins(configured: str) -> tuple[str, ...]:
    origins: list[str] = []
    for raw_origin in configured.split(","):
        if not (origin := raw_origin.strip()):
            continue
        normalized = _normalize_origin(origin)
        if normalized not in origins:
            origins.append(normalized)
    return tuple(origins)


def _normalize_origin(origin: str) -> str:
    if origin == "*":
        raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard")

    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "CORS_ALLOWED_ORIGINS entries must be HTTP(S) origins without paths"
        )
    return f"{parsed.scheme}://{parsed.netloc}"
