"""
Bitcoin BTC/EUR daily history fetcher.

Uses the Bitstamp public OHLC endpoint (no API key required), which serves
several years of daily candles via pagination.

Why not the alternatives:
  - CoinGecko free tier rejects ranges beyond 365 days (error 10012).
  - Kraken's OHLC endpoint caps at ~720 candles regardless of `since`.

Both of those silently produced too little data for a multi-year backtest,
which is what let synthetic prices reach the database previously.
"""
import datetime as dt
import time
from decimal import Decimal
from typing import Dict

import httpx

BITSTAMP_OHLC_URL = "https://www.bitstamp.net/api/v2/ohlc/btceur/"
STEP_DAILY = 86400
PAGE_LIMIT = 1000
DEFAULT_START = dt.date(2017, 1, 1)

# Sanity bounds for a BTC/EUR close. Anything outside this is not a real
# price and must not be written to the database.
MIN_PLAUSIBLE_EUR = Decimal("100")
MAX_PLAUSIBLE_EUR = Decimal("1000000")


class BitcoinDataError(RuntimeError):
    """Raised when real price data cannot be retrieved or fails validation."""


def _get_page(start_ts: int, retries: int = 4) -> list:
    last_error = None
    for attempt in range(retries):
        try:
            response = httpx.get(
                BITSTAMP_OHLC_URL,
                params={"step": STEP_DAILY, "limit": PAGE_LIMIT, "start": start_ts},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["data"]["ohlc"]
        except Exception as exc:  # network flake, rate limit, shape change
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    raise BitcoinDataError(
        f"Bitstamp request failed after {retries} attempts: {last_error}"
    )


def fetch_btc_eur_daily(start: dt.date = DEFAULT_START) -> Dict[dt.date, Decimal]:
    """
    Fetch real daily BTC/EUR closing prices from `start` to today.

    Returns a date -> Decimal price mapping. Raises BitcoinDataError rather
    than falling back to synthetic data.
    """
    start_ts = int(dt.datetime(start.year, start.month, start.day,
                               tzinfo=dt.timezone.utc).timestamp())
    prices: Dict[dt.date, Decimal] = {}

    while True:
        page = _get_page(start_ts)
        if not page:
            break

        for candle in page:
            day = dt.datetime.fromtimestamp(
                int(candle["timestamp"]), dt.timezone.utc
            ).date()
            price = Decimal(str(candle["close"]))
            if price <= 0:
                continue  # exchange gap, no trades recorded
            prices[day] = price

        if len(page) < PAGE_LIMIT:
            break
        start_ts = int(page[-1]["timestamp"]) + STEP_DAILY

    validate_prices(prices)
    return prices


def validate_prices(prices: Dict[dt.date, Decimal], min_days: int = 1000) -> None:
    """
    Guard against silently seeding bad data.

    Checks volume, price plausibility, and freshness. Raises BitcoinDataError
    on any failure so a broken fetch aborts the seed instead of writing
    made-up numbers to the database.
    """
    if len(prices) < min_days:
        raise BitcoinDataError(
            f"Only {len(prices)} daily prices returned, expected at least "
            f"{min_days}. Refusing to seed a partial history."
        )

    out_of_range = [
        (day, price)
        for day, price in prices.items()
        if not (MIN_PLAUSIBLE_EUR <= price <= MAX_PLAUSIBLE_EUR)
    ]
    if out_of_range:
        raise BitcoinDataError(
            f"{len(out_of_range)} prices outside plausible BTC/EUR range, "
            f"e.g. {out_of_range[:3]}"
        )

    newest = max(prices)
    staleness = (dt.date.today() - newest).days
    if staleness > 7:
        raise BitcoinDataError(
            f"Newest price is {newest} ({staleness} days old). Source is stale."
        )
