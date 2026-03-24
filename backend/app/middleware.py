"""Application middleware — error handling, rate limiting, request logging."""

from __future__ import annotations

import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("agent_sandbox")


# ── Structured error handling ───────────────────────────────────────────────

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns structured JSON errors."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error_type": type(exc).__name__,
                    "path": request.url.path,
                },
            )


# ── Rate limiting ───────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter keyed by client IP.

    Defaults: 100 requests per 60-second window.
    Write endpoints (POST/PUT/DELETE) get a stricter limit of 30/min.
    """

    def __init__(self, app, read_limit: int = 100, write_limit: int = 30, window: int = 60):
        super().__init__(app)
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.window = window
        self._read_hits: dict[str, list[float]] = defaultdict(list)
        self._write_hits: dict[str, list[float]] = defaultdict(list)

    def _prune(self, hits: list[float], now: float) -> list[float]:
        cutoff = now - self.window
        return [t for t in hits if t > cutoff]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks, WebSocket upgrades, and test clients
        if request.url.path == "/api/health" or request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if client_ip == "testclient":
            return await call_next(request)
        now = time.time()
        is_write = request.method in ("POST", "PUT", "DELETE", "PATCH")

        if is_write:
            self._write_hits[client_ip] = self._prune(self._write_hits[client_ip], now)
            if len(self._write_hits[client_ip]) >= self.write_limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "retry_after": self.window},
                    headers={"Retry-After": str(self.window)},
                )
            self._write_hits[client_ip].append(now)
        else:
            self._read_hits[client_ip] = self._prune(self._read_hits[client_ip], now)
            if len(self._read_hits[client_ip]) >= self.read_limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "retry_after": self.window},
                    headers={"Retry-After": str(self.window)},
                )
            self._read_hits[client_ip].append(now)

        return await call_next(request)


# ── Request logging ─────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request method, path, status code, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        t0 = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "%s %s → %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
