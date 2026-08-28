"""
Shared rate limiter.

The portfolio endpoints run a full historical backtest per request, which is
comparatively expensive, so they are limited per client IP. Defined in its own
module so routes and the app factory import the same limiter instance.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

limiter = Limiter(key_func=get_remote_address)

# Applied to the calculation endpoints via @limiter.limit(...).
CALCULATION_RATE_LIMIT = f"{settings.RATE_LIMIT_PER_MINUTE}/minute"
