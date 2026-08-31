"""
Tests for recurring contributions (DCA) in the portfolio engine.

The bug these guard against: the engine bought units once at the start and
ignored the monthly contribution the UI collects, so a saver paying in every
month saw a figure computed as if they never had.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pandas as pd
import pytest

from services.portfolio_calculator import PortfolioCalculator
from models.portfolio import PortfolioCalculationRequest, PortfolioAllocation

PPR_ID = "550e8400-e29b-41d4-a716-446655440000"


def _request(**overrides) -> PortfolioCalculationRequest:
    params = dict(
        ppr_allocations=[
            PortfolioAllocation(ppr_id=PPR_ID, allocation_percentage=Decimal("100"))
        ],
        bitcoin_percentage=Decimal("0"),
        initial_investment=Decimal("10000"),
        start_date=date(2020, 1, 1),
        end_date=date(2023, 1, 1),
        rebalancing_frequency="none",
    )
    params.update(overrides)
    return PortfolioCalculationRequest(**params)


def _flat_data(days: int = 1096, price: float = 10.0) -> pd.DataFrame:
    """A perfectly flat price series: any gain must come from contributions."""
    idx = pd.date_range("2020-01-01", periods=days, freq="D")
    return pd.DataFrame({f"ppr_{PPR_ID}": [price] * days}, index=idx)


def _growing_data(days: int = 1096, start: float = 10.0, end: float = 20.0) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=days, freq="D")
    prices = [start + (end - start) * i / (days - 1) for i in range(days)]
    return pd.DataFrame({f"ppr_{PPR_ID}": prices}, index=idx)


class TestContributionsAreInvested:
    """Contributions must actually reach the portfolio."""

    def test_contributions_increase_final_value(self):
        """
        The core regression. On a flat price series, a portfolio with monthly
        contributions must end worth more than one without -- before this fix
        the two were identical.
        """
        calc = PortfolioCalculator(Mock())
        data = _flat_data()

        lump = calc._calculate_portfolio_values(data, _request(), {})
        dca = calc._calculate_portfolio_values(
            data,
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )

        assert dca.iloc[-1]["total_value"] > lump.iloc[-1]["total_value"]

    def test_flat_prices_means_value_equals_capital(self):
        """
        With a flat price nothing is earned, so the final value must equal
        every euro paid in -- no more (units conjured) and no less (cash lost).
        """
        calc = PortfolioCalculator(Mock())
        result = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        final = result.iloc[-1]
        assert final["total_value"] == pytest.approx(final["invested_capital"], rel=1e-9)

    def test_invested_capital_is_monotonic(self):
        """Capital paid in can only ever rise."""
        calc = PortfolioCalculator(Mock())
        result = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        capital = result["invested_capital"].tolist()
        assert capital[0] == pytest.approx(10000.0)
        assert all(b >= a for a, b in zip(capital, capital[1:]))

    def test_no_contribution_leaves_capital_flat(self):
        """A lump sum pays in once; the running total must never move."""
        calc = PortfolioCalculator(Mock())
        result = calc._calculate_portfolio_values(_flat_data(), _request(), {})
        assert result["invested_capital"].nunique() == 1
        assert result.iloc[-1]["invested_capital"] == pytest.approx(10000.0)

    def test_quarterly_pays_in_less_often_than_monthly(self):
        calc = PortfolioCalculator(Mock())
        data = _flat_data()
        monthly = calc._calculate_portfolio_values(
            data,
            _request(contribution_amount=Decimal("300"), contribution_frequency="monthly"),
            {},
        )
        quarterly = calc._calculate_portfolio_values(
            data,
            _request(contribution_amount=Decimal("300"), contribution_frequency="quarterly"),
            {},
        )
        assert (
            quarterly.iloc[-1]["invested_capital"]
            < monthly.iloc[-1]["invested_capital"]
        )

    def test_frequency_none_ignores_amount(self):
        """An amount with no schedule must not be invested."""
        calc = PortfolioCalculator(Mock())
        result = calc._calculate_portfolio_values(
            _flat_data(),
            _request(contribution_amount=Decimal("500"), contribution_frequency="none"),
            {},
        )
        assert result.iloc[-1]["invested_capital"] == pytest.approx(10000.0)


class TestMetricsWithContributions:
    """
    The metrics must not treat contributed cash as investment performance.
    This is the silent-wrongness half of the bug.
    """

    def test_flat_prices_show_no_return(self):
        """
        Paying into a flat fund earns nothing. If contributions leaked into
        the return, this would show a large fictitious profit.
        """
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        metrics = calc._calculate_performance_metrics(values, Decimal("10000"))

        assert float(metrics.total_return) == pytest.approx(0.0, abs=1e-6)
        assert float(metrics.total_return_percentage) == pytest.approx(0.0, abs=1e-6)
        assert float(metrics.irr) == pytest.approx(0.0, abs=0.01)

    def test_invested_capital_reported(self):
        """36 monthly payments of 200 on top of 10,000."""
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        metrics = calc._calculate_performance_metrics(values, Decimal("10000"))
        assert float(metrics.invested_capital) > 10000.0
        assert metrics.is_money_weighted is True

    def test_lump_sum_is_not_money_weighted(self):
        """Without contributions the old behaviour must be untouched."""
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(_growing_data(), _request(), {})
        metrics = calc._calculate_performance_metrics(values, Decimal("10000"))

        assert metrics.is_money_weighted is False
        assert float(metrics.invested_capital) == pytest.approx(10000.0)
        # Price doubled, so the lump sum doubled.
        assert float(metrics.total_return_percentage) == pytest.approx(100.0, abs=0.5)

    def test_lump_sum_irr_matches_cagr(self):
        """
        With a single cashflow in and one out, the money-weighted and
        time-weighted returns are the same number by definition.
        """
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(_growing_data(), _request(), {})
        metrics = calc._calculate_performance_metrics(values, Decimal("10000"))

        assert metrics.irr is not None
        assert float(metrics.irr) == pytest.approx(float(metrics.cagr), abs=0.1)

    def test_contributions_do_not_inflate_volatility(self):
        """
        A flat price series has zero volatility. If contributions were read as
        daily returns, every payday would register as a jump.
        """
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        metrics = calc._calculate_performance_metrics(values, Decimal("10000"))
        assert float(metrics.volatility) == pytest.approx(0.0, abs=1e-6)
        assert float(metrics.max_drawdown) == pytest.approx(0.0, abs=1e-6)

    def test_dca_return_is_not_the_naive_ratio(self):
        """
        On a rising series, money paid in late compounds for less time, so the
        IRR must exceed the naive profit-over-capital ratio. Reporting the
        naive figure as an annual return is the error being prevented.
        """
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            _growing_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        metrics = calc._calculate_performance_metrics(values, Decimal("10000"))
        assert metrics.irr is not None
        assert float(metrics.irr) > float(metrics.total_return_percentage) / 3.0


class TestHistoricalSeries:
    """The chart series must stay honest about contributions too."""

    def test_no_fake_gain_on_contribution_day(self):
        """
        On flat prices the cumulative return line must sit at zero throughout.
        Measuring against the initial investment alone would make it climb
        with every payment.
        """
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        points = calc._build_historical_data_points(values)
        assert max(abs(float(p.total_return)) for p in points) < 1e-6

    def test_invested_capital_exposed_to_chart(self):
        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            _flat_data(),
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        points = calc._build_historical_data_points(values)
        assert float(points[0].invested_capital) == pytest.approx(10000.0)
        assert float(points[-1].invested_capital) > 10000.0

    def test_contribution_does_not_mask_drawdown(self):
        """
        A falling price with contributions must still register a drawdown.
        Tracking the peak on raw value would let each payment reset the peak
        and hide the loss.
        """
        idx = pd.date_range("2020-01-01", periods=400, freq="D")
        prices = [10.0 - 5.0 * i / 399 for i in range(400)]
        data = pd.DataFrame({f"ppr_{PPR_ID}": prices}, index=idx)

        calc = PortfolioCalculator(Mock())
        values = calc._calculate_portfolio_values(
            data,
            _request(
                contribution_amount=Decimal("200"),
                contribution_frequency="monthly",
            ),
            {},
        )
        points = calc._build_historical_data_points(values)
        assert min(float(p.drawdown) for p in points) < -30.0
