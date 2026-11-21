"""In-process, per-client rate limiting for write endpoints that cost money or accept uploads.

State lives in this process; run one API replica or move the counters to a shared store before
scaling out.
"""
from threading import Lock
from time import monotonic

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from apps.backend.core.config import API_PREFIX
from apps.backend.core.exceptions import error_response

WINDOW_SECONDS = 60
MAX_TRACKED_CLIENTS = 4096
GENERATION_PATHS = {"/ai/generate", "/roadmaps", "/projects"}
SUBMISSION_PATHS = {"/contributions", "/portfolio/upload"}


def bucket_for(path: str) -> tuple[str, int] | None:
    if path.startswith(API_PREFIX + "/"):
        path = path[len(API_PREFIX):]
    if path.startswith("/auth/"):
        return "auth", 30
    if path in GENERATION_PATHS or (path.startswith("/portfolio/") and path.endswith("/evaluate")):
        return "generation", 30
    if path in SUBMISSION_PATHS:
        return "submission", 30
    return None


class RateLimiter:
    def __init__(self):
        self._lock = Lock()
        self._windows: dict[str, list[float]] = {}

    def reset(self) -> None:
        with self._lock:
            self._windows.clear()

    def retry_after(self, key: str, limit: int) -> int | None:
        """Record a request and return the seconds to wait if the client is over its limit."""
        now = monotonic()
        with self._lock:
            for expired in [entry for entry, times in self._windows.items() if now - times[-1] >= WINDOW_SECONDS]:
                del self._windows[expired]
            recent = [stamp for stamp in self._windows.get(key, []) if now - stamp < WINDOW_SECONDS]
            if len(recent) >= limit or (key not in self._windows and len(self._windows) >= MAX_TRACKED_CLIENTS):
                return max(1, WINDOW_SECONDS - int(now - recent[0])) if recent else WINDOW_SECONDS
            recent.append(now)
            self._windows[key] = recent
        return None


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST":
            return await call_next(request)
        bucket = bucket_for(request.url.path)
        if bucket is None:
            return await call_next(request)
        name, limit = bucket
        key = f"{request.client.host if request.client else 'unknown'}:{name}"
        retry_after = rate_limiter.retry_after(key, limit)
        if retry_after is not None:
            return error_response(429, "Too many requests. Please wait before trying again.", "rate_limited",
                                  headers={"Retry-After": str(retry_after)})
        return await call_next(request)
