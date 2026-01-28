"""
Rate limiting middleware for photo search endpoints
"""
from fastapi import Request, HTTPException
from typing import Dict
import time
import logging

logger = logging.getLogger(__name__)


class PhotoSearchRateLimiter:
    """
    Rate limiter for photo search requests
    Prevents abuse and controls API costs
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60
    ):
        """
        Args:
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}  # IP -> list of timestamps

    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if client has exceeded rate limit

        Args:
            client_ip: Client IP address

        Returns:
            True if allowed, raises HTTPException if rate limit exceeded
        """
        now = time.time()

        # Get or create request history for this IP
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Remove old requests outside the time window
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip]
            if now - ts < self.window_seconds
        ]

        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"🚫 Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} photo searches per {self.window_seconds} seconds."
            )

        # Add current request
        self.requests[client_ip].append(now)
        remaining = self.max_requests - len(self.requests[client_ip])
        logger.info(f"✅ Rate limit check passed for {client_ip} ({remaining} remaining)")

        return True

    def get_remaining(self, client_ip: str) -> int:
        """Get remaining requests for client"""
        if client_ip not in self.requests:
            return self.max_requests

        now = time.time()
        recent_requests = [
            ts for ts in self.requests[client_ip]
            if now - ts < self.window_seconds
        ]

        return max(0, self.max_requests - len(recent_requests))

    def cleanup_old_entries(self):
        """Remove old entries to prevent memory growth"""
        now = time.time()

        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if now - ts < self.window_seconds
            ]

            # Remove IP if no recent requests
            if not self.requests[ip]:
                del self.requests[ip]


# Global rate limiter instance
photo_rate_limiter = PhotoSearchRateLimiter(
    max_requests=10,  # 10 photo searches
    window_seconds=60  # per minute
)
