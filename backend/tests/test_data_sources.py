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
class TestHistoricalAlignment:
    """
    Regression tests for _align_historical_data.

    PPR funds quote on business days while Bitcoin trades every day, so the
    two series have different indexes. pandas.concat unions them in
    concatenation order rather than date order; the resulting unsorted index
    made ffill carry values backwards in time and produced a flat tail on the
    chart plus meaningless daily returns.
    """

    def _calculator(self):
        from services.portfolio_calculator import PortfolioCalculator
        return PortfolioCalculator(db=None)

    def _frames(self):
        import pandas as pd

        # PPR: business days only.
        ppr_index = pd.bdate_range("2024-01-01", "2024-03-29")
        ppr = pd.DataFrame(
            {"ppr_x": range(len(ppr_index))}, index=ppr_index
        )
        # Bitcoin: every calendar day, extending past the last PPR quote.
        btc_index = pd.date_range("2024-01-01", "2024-04-15")
        btc = pd.DataFrame(
            {"bitcoin_price": range(len(btc_index))}, index=btc_index
        )
        return ppr, btc

    def test_aligned_index_is_sorted(self):
        ppr, btc = self._frames()
        combined = self._calculator()._align_historical_data(ppr, btc)
        assert combined.index.is_monotonic_increasing

    def test_no_dates_after_last_ppr_quote(self):
        """Trailing Bitcoin-only days would repeat the last PPR quote."""
        ppr, btc = self._frames()
        combined = self._calculator()._align_historical_data(ppr, btc)
        assert combined.index.max() == ppr.index.max()

    def test_no_repeated_flat_tail(self):
        """The last values must not be a run of identical numbers."""
        ppr, btc = self._frames()
        combined = self._calculator()._align_historical_data(ppr, btc)
        tail = combined["ppr_x"].tail(5).tolist()
        assert len(set(tail)) > 1
