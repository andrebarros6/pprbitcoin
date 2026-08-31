"""
Tests for the "same plan, no Bitcoin" comparison line.

This is the core question of the tool -- what did adding Bitcoin actually
change? -- so the two series must differ in exactly one respect and nothing
else.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pandas as pd
import pytest

from services.portfolio_calculator import PortfolioCalculator
from models.portfolio import PortfolioCalculationRequest, PortfolioAllocation

PPR_ID = "550e8400-e29b-41d4-a716-446655440000"
PPR_ID_B = "550e8400-e29b-41d4-a716-446655440001"


def _request(**overrides) -> PortfolioCalculationRequest:
    params = dict(
        ppr_allocations=[
            PortfolioAllocation(ppr_id=PPR_ID, allocation_percentage=Decimal("80"))
        ],
        bitcoin_percentage=Decimal("20"),
        initial_investment=Decimal("10000"),
        start_date=date(2020, 1, 1),
        end_date=date(2023, 1, 1),
        rebalancing_frequency="none",
    )
    params.update(overrides)
    return PortfolioCalculationRequest(**params)


def _data(days: int = 800, btc_end: float = 40000.0) -> pd.DataFrame:
    """PPR grows modestly; Bitcoin grows a lot."""
    idx = pd.date_range("2020-01-01", periods=days, freq="D")
    return pd.DataFrame(
        {
            f"ppr_{PPR_ID}": [10.0 + 2.0 * i / (days - 1) for i in range(days)],
            "bitcoin_price": [
                10000.0 + (btc_end - 10000.0) * i / (days - 1) for i in range(days)
            ],
        },
        index=idx,
    )


class TestWithoutBitcoinReference:
    def test_absent_when_no_bitcoin(self):
        """A PPR-only portfolio has no counterfactual worth showing."""
        calc = PortfolioCalculator(Mock())
        req = _request(
            bitcoin_percentage=Decimal("0"),
            ppr_allocations=[
                PortfolioAllocation(ppr_id=PPR_ID, allocation_percentage=Decimal("100"))
            ],
        )
        assert calc._calculate_without_bitcoin(req, _data(), {}) is None

    def test_present_when_bitcoin_held(self):
        calc = PortfolioCalculator(Mock())
        ref = calc._calculate_without_bitcoin(_request(), _data(), {})
        assert ref is not None
        assert ref.label == "Sem Bitcoin (só PPR)"

    def test_reference_starts_at_full_initial_investment(self):
        """
        The PPR weights are scaled to 100%, so the comparison must invest the
        whole initial amount -- not just the 80% that was in PPR.
        """
        calc = PortfolioCalculator(Mock())
        ref = calc._calculate_without_bitcoin(_request(), _data(), {})
        assert float(ref.historical_data[0].portfolio_value) == pytest.approx(
            10000.0, rel=1e-6
        )

    def test_reference_holds_no_bitcoin(self):
        calc = PortfolioCalculator(Mock())
        ref = calc._calculate_without_bitcoin(_request(), _data(), {})
        assert all(
            float(p.bitcoin_value) == 0.0 for p in ref.historical_data
        )

    def test_rising_bitcoin_beats_the_reference(self):
        """With Bitcoin outperforming, the real portfolio must end ahead."""
        calc = PortfolioCalculator(Mock())
        data = _data()
        req = _request()

        main = calc._calculate_portfolio_values(data, req, {})
        ref = calc._calculate_without_bitcoin(req, data, {})

        assert main.iloc[-1]["total_value"] > float(ref.metrics.final_value)

    def test_falling_bitcoin_loses_to_the_reference(self):
        """The comparison must be able to favour PPR, or it proves nothing."""
        calc = PortfolioCalculator(Mock())
        data = _data(btc_end=2000.0)  # Bitcoin collapses
        req = _request()

        main = calc._calculate_portfolio_values(data, req, {})
        ref = calc._calculate_without_bitcoin(req, data, {})

        assert main.iloc[-1]["total_value"] < float(ref.metrics.final_value)

    def test_series_are_date_aligned(self):
        """
        Both lines are drawn on one chart, so they must cover identical dates.
        """
        calc = PortfolioCalculator(Mock())
        data = _data()
        req = _request()

        main = calc._calculate_portfolio_values(data, req, {})
        ref = calc._calculate_without_bitcoin(req, data, {})

        assert len(ref.historical_data) == len(main)
        assert ref.historical_data[0].data == main.iloc[0]["date"]
        assert ref.historical_data[-1].data == main.iloc[-1]["date"]

    def test_contributions_carry_into_the_reference(self):
        """
        The comparison must use the same savings plan. If contributions were
        dropped, it would understate the PPR-only outcome and flatter Bitcoin.
        """
        calc = PortfolioCalculator(Mock())
        req = _request(
            contribution_amount=Decimal("200"),
            contribution_frequency="monthly",
        )
        ref = calc._calculate_without_bitcoin(req, _data(), {})
        assert float(ref.metrics.invested_capital) > 10000.0
        assert ref.metrics.is_money_weighted is True

    def test_multiple_pprs_keep_their_relative_weights(self):
        """
        Scaling to 100% must preserve the ratio between funds -- a 60/20 split
        becomes 75/25, not 50/50.
        """
        calc = PortfolioCalculator(Mock())
        idx = pd.date_range("2020-01-01", periods=400, freq="D")
        data = pd.DataFrame(
            {
                f"ppr_{PPR_ID}": [10.0] * 400,
                f"ppr_{PPR_ID_B}": [10.0] * 400,
                "bitcoin_price": [10000.0] * 400,
            },
            index=idx,
        )
        req = _request(
            ppr_allocations=[
                PortfolioAllocation(ppr_id=PPR_ID, allocation_percentage=Decimal("60")),
                PortfolioAllocation(ppr_id=PPR_ID_B, allocation_percentage=Decimal("20")),
            ],
            bitcoin_percentage=Decimal("20"),
        )
        ref = calc._calculate_without_bitcoin(req, data, {})
        # Flat prices, so the whole 10,000 is simply held.
        assert float(ref.historical_data[-1].portfolio_value) == pytest.approx(
            10000.0, rel=1e-6
        )

    def test_main_metrics_unaffected_by_the_reference_run(self):
        """
        Both runs share the calculator instance and the IRR cashflow buffer
        lives on it. Computing the comparison must not corrupt the main
        result's own IRR.
        """
        calc = PortfolioCalculator(Mock())
        data = _data()
        req = _request(
            contribution_amount=Decimal("200"),
            contribution_frequency="monthly",
        )

        values = calc._calculate_portfolio_values(data, req, {})
        before = calc._calculate_performance_metrics(values, req.initial_investment)

        calc._calculate_without_bitcoin(req, data, {})

        after = calc._calculate_performance_metrics(values, req.initial_investment)
        assert after.irr == before.irr
