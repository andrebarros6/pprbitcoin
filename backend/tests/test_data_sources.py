"""
Tests for the real-data fetchers and their validation guards.

The point of these tests is that a failed or degraded fetch must raise, never
silently substitute synthetic data. That substitution is what previously put
a random walk into the database and presented it as Bitcoin's price history.
"""
import datetime as dt
from decimal import Decimal

import pytest

from services.bitcoin_history import (
    BitcoinDataError,
    validate_prices,
)
from services.ppr_history import (
    PPRDataError,
    validate_nav,
)


def _good_prices(n=1500, start_price=20000):
    """A plausible, fresh BTC/EUR series ending today."""
    today = dt.date.today()
    return {
        today - dt.timedelta(days=i): Decimal(start_price + i)
        for i in range(n)
    }


def _good_nav(n=800, start=10):
    today = dt.date.today()
    return {
        today - dt.timedelta(days=i): Decimal(str(start + i * 0.001))
        for i in range(n)
    }


class TestBitcoinValidation:
    def test_accepts_plausible_series(self):
        validate_prices(_good_prices())  # must not raise

    def test_rejects_too_few_days(self):
        prices = _good_prices(n=100)
        with pytest.raises(BitcoinDataError, match="Refusing to seed"):
            validate_prices(prices)

    def test_rejects_implausible_low_price(self):
        """The old synthetic fallback started at EUR 1000 and stayed there."""
        prices = _good_prices()
        prices[dt.date.today()] = Decimal("50")
        with pytest.raises(BitcoinDataError, match="outside plausible"):
            validate_prices(prices)

    def test_rejects_implausible_high_price(self):
        prices = _good_prices()
        prices[dt.date.today()] = Decimal("5000000")
        with pytest.raises(BitcoinDataError, match="outside plausible"):
            validate_prices(prices)

    def test_rejects_stale_series(self):
        old = dt.date.today() - dt.timedelta(days=60)
        prices = {old - dt.timedelta(days=i): Decimal(20000 + i) for i in range(1500)}
        with pytest.raises(BitcoinDataError, match="stale"):
            validate_prices(prices)


class TestPPRValidation:
    def test_accepts_plausible_series(self):
        validate_nav("Test Fund", _good_nav())  # must not raise

    def test_rejects_too_few_observations(self):
        with pytest.raises(PPRDataError, match="expected"):
            validate_nav("Test Fund", _good_nav(n=50))

    def test_rejects_implausible_nav(self):
        nav = _good_nav()
        nav[dt.date.today()] = Decimal("5000")
        with pytest.raises(PPRDataError, match="implausible NAV"):
            validate_nav("Test Fund", nav)

    def test_rejects_stale_series(self):
        old = dt.date.today() - dt.timedelta(days=45)
        nav = {old - dt.timedelta(days=i): Decimal("10") for i in range(800)}
        with pytest.raises(PPRDataError, match="stale"):
            validate_nav("Test Fund", nav)

    def test_rejects_implausible_daily_jump(self):
        """A >35% single-day move means a split or a parse error, not a fund."""
        today = dt.date.today()
        nav = {today - dt.timedelta(days=i): Decimal("10") for i in range(800)}
        nav[today] = Decimal("50")
        with pytest.raises(PPRDataError, match="implausible"):
            validate_nav("Test Fund", nav)

    def test_tolerates_gaps_in_reporting(self):
        """Genuine reporting gaps (weekends, holidays) must not trip the jump check."""
        today = dt.date.today()
        nav = {}
        day = today
        for i in range(800):
            nav[day] = Decimal("10") + Decimal(i) / 1000
            day -= dt.timedelta(days=3 if i % 5 == 0 else 1)
        validate_nav("Test Fund", nav)  # must not raise
