"""Small in-process rate limiter for abuse-prone endpoints.

Sliding-window counter keyed by client IP. In-memory state is fine for the
current single-instance deployment; swap for a Redis-backed limiter if the
backend is ever scaled horizontally.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """FastAPI dependency: allow at most `times` requests per `seconds` per IP."""

    def __init__(self, times: int, seconds: int) -> None:
        self.times = times
        self.seconds = seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, request: Request) -> None:
        if request.client is None:  # e.g. some test transports
            return
        key = request.client.host
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self.seconds:
            window.popleft()
        if len(window) >= self.times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
            )
        window.append(now)


# Sybil gate: registrations are the cheapest way to manufacture fake
# consensus, so they are throttled hardest.
register_rate_limiter = RateLimiter(times=5, seconds=15 * 60)
login_rate_limiter = RateLimiter(times=10, seconds=60)
