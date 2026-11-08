"""Thread-safe, in-memory sliding-window rate limiter for CLIMAFORGE.

Provides a lightweight alternative to slowapi/Redis for the login endpoint.
State is stored in process memory, so limits reset on restart; sufficient for
the current deployment model.
"""

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Fixed in-memory sliding-window limiter keyed on arbitrary string keys (e.g. client IP).

    Not distributed — suitable only for single-process deployments.  Replace
    with a Redis-backed implementation when horizontal scaling is introduced.
    """

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")

        self._max_calls = max_calls
        self._window = window_seconds
        self._lock = threading.Lock()
        # key → deque of Unix timestamps of accepted requests
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        """Return True if the request is within the rate limit, False if it should be rejected."""
        now = time.monotonic()
        cutoff = now - self._window

        with self._lock:
            dq = self._windows[key]

            # Evict timestamps outside the current window
            while dq and dq[0] <= cutoff:
                dq.popleft()

            if len(dq) >= self._max_calls:
                return False

            dq.append(now)
            return True

    def reset(self, key: str) -> None:
        """Remove all recorded calls for a key (useful in tests)."""
        with self._lock:
            self._windows.pop(key, None)

    def reset_all(self) -> None:
        """Clear all rate-limit state (useful in tests)."""
        with self._lock:
            self._windows.clear()


# Default limiter: 5 login attempts per 60-second sliding window per client IP.
login_limiter = SlidingWindowRateLimiter(max_calls=5, window_seconds=60.0)

