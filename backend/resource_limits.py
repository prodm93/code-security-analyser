"""Request-size and concurrency controls for analysis endpoints."""

import asyncio
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_MEBIBYTE = 1024 * 1024
_MULTIPART_OVERHEAD_BYTES = 128 * 1024


@dataclass(frozen=True)
class ProjectArchiveLimits:
    max_upload_bytes: int
    max_extracted_bytes: int
    max_members: int


@dataclass(frozen=True)
class ResourceLimits:
    code_request_bytes: int
    image_request_bytes: int
    project_archive: ProjectArchiveLimits
    max_concurrent_analyses: int
    queue_timeout_seconds: float

    @classmethod
    def from_environment(
        cls, source: Mapping[str, str] | None = None
    ) -> "ResourceLimits":
        values = os.environ if source is None else source
        return cls(
            code_request_bytes=_positive_int(
                values, "MAX_CODE_REQUEST_BYTES", _MEBIBYTE
            ),
            image_request_bytes=_positive_int(
                values, "MAX_IMAGE_REQUEST_BYTES", 16 * 1024
            ),
            project_archive=ProjectArchiveLimits(
                max_upload_bytes=_positive_int(
                    values, "MAX_PROJECT_UPLOAD_BYTES", 10 * _MEBIBYTE
                ),
                max_extracted_bytes=_positive_int(
                    values, "MAX_PROJECT_EXTRACTED_BYTES", 50 * _MEBIBYTE
                ),
                max_members=_positive_int(values, "MAX_PROJECT_FILES", 2_000),
            ),
            max_concurrent_analyses=_positive_int(values, "MAX_CONCURRENT_ANALYSES", 1),
            queue_timeout_seconds=_positive_float(
                values, "ANALYSIS_QUEUE_TIMEOUT_SECONDS", 1.0
            ),
        )

    @property
    def request_body_limits(self) -> dict[str, int]:
        return {
            "/api/analyze": self.code_request_bytes,
            "/api/analyze-image": self.image_request_bytes,
            "/api/analyze-project": (
                self.project_archive.max_upload_bytes + _MULTIPART_OVERHEAD_BYTES
            ),
        }


class AnalysisCapacityExceeded(Exception):
    """Raised when an analysis slot is not available promptly."""


class AnalysisCapacity:
    def __init__(self, maximum: int, queue_timeout_seconds: float) -> None:
        self._semaphore = asyncio.BoundedSemaphore(maximum)
        self._queue_timeout_seconds = queue_timeout_seconds

    @asynccontextmanager
    async def reserve(self) -> AsyncIterator[None]:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(), timeout=self._queue_timeout_seconds
            )
        except TimeoutError as exc:
            raise AnalysisCapacityExceeded from exc

        try:
            yield
        finally:
            self._semaphore.release()


class _RequestBodyTooLarge(OSError):
    """Use OSError so Starlette closes partial multipart spool files."""

    pass


class RequestBodyLimitMiddleware:
    """Reject oversized analysis bodies before FastAPI parses them."""

    def __init__(self, app: ASGIApp, path_limits: Mapping[str, int]) -> None:
        self._app = app
        self._path_limits = dict(path_limits)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        limit = self._path_limits.get(scope.get("path", ""))
        if limit is None:
            await self._app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > limit:
            await _send_too_large(scope, receive, send, limit)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _RequestBodyTooLarge
            return message

        try:
            await self._app(scope, limited_receive, send)
        except _RequestBodyTooLarge:
            await _send_too_large(scope, receive, send, limit)


def _content_length(scope: Scope) -> int | None:
    value = Headers(scope=scope).get("content-length")
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


async def _send_too_large(
    scope: Scope, receive: Receive, send: Send, limit: int
) -> None:
    response = JSONResponse(
        {"detail": f"Request body exceeds the {limit}-byte limit"},
        status_code=413,
    )
    await response(scope, receive, send)


def _positive_int(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _positive_float(values: Mapping[str, str], name: str, default: float) -> float:
    raw = values.get(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return value
