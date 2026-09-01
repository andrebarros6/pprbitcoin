"""
Shared rate limiter.

The portfolio endpoints run a full historical backtest per request, which is
comparatively expensive, so they are limited per client IP. Defined in its own
module so routes and the app factory import the same limiter instance.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from config import settings


def client_ip(request: Request) -> str:
    """
    Identify the caller for rate limiting.

    Behind a proxy the socket peer is the proxy itself, so every request looks
    like one client and the limit never fires -- which is exactly what
    production did: 250 sequential calls, zero 429s. The real client is the
    first entry of X-Forwarded-For, which the proxy appends to.

    That header is trivially forged when it reaches us directly, so it is only
    trusted when TRUST_PROXY_HEADERS is set. Deployments behind Railway, Fly,
    Heroku or an nginx ingress should set it; a directly-exposed server must
    not, or any caller could spoof a fresh IP per request and bypass the limit
    entirely.
    """
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Left-most entry is the original client; the rest are proxy hops.
            first = forwarded.split(",")[0].strip()
            if first:
                return first

    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)

# Applied to the calculation endpoints via @limiter.limit(...).
#
# The counter lives in each worker's memory, so with N workers a determined
# caller can reach roughly N times this number before being throttled. That is
# acceptable for shedding accidental load, which is what this limit is for. A
# limit meant to resist deliberate abuse needs shared storage (Limiter accepts
# a Redis storage_uri) so all workers count against the same tally.
CALCULATION_RATE_LIMIT = f"{settings.RATE_LIMIT_PER_MINUTE}/minute"
