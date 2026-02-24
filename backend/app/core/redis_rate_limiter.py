"""
ตัวจำกัดอัตรา (Rate Limiter) แบบ in-memory (Redis ถูกลบออกแล้ว)
"""

import time
from collections import defaultdict
from typing import Tuple, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """
    In-memory rate limiter (Redis removed).
    API-compatible — same method signatures as the Redis version.
    Uses sliding window algorithm.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        fallback_to_memory: bool = True,  # kept for API compatibility
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._memory_requests: dict = defaultdict(list)

    def _make_key(self, identifier: str) -> str:
        return f"ratelimit:{identifier}"

    async def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        return self._is_allowed_memory(identifier)

    def _is_allowed_memory(self, identifier: str) -> Tuple[bool, int]:
        current_time = time.time()

        self._memory_requests[identifier] = [
            req_time
            for req_time in self._memory_requests[identifier]
            if current_time - req_time < self.window_seconds
        ]

        request_count = len(self._memory_requests[identifier])

        if request_count >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {identifier}: {request_count}/{self.max_requests}"
            )
            return False, 0

        self._memory_requests[identifier].append(current_time)
        remaining = self.max_requests - len(self._memory_requests[identifier])
        return True, remaining

    async def reset(self, identifier: Optional[str] = None) -> bool:
        if identifier:
            self._memory_requests.pop(identifier, None)
        else:
            self._memory_requests.clear()
        return True

    async def get_remaining(self, identifier: str) -> int:
        current_time = time.time()
        if identifier in self._memory_requests:
            self._memory_requests[identifier] = [
                req_time
                for req_time in self._memory_requests[identifier]
                if current_time - req_time < self.window_seconds
            ]
        count = len(self._memory_requests.get(identifier, []))
        return max(0, self.max_requests - count)
