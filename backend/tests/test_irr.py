"""
Tests for the money-weighted return (XIRR) solver.

Every case here is checked against a value computed independently of the
implementation -- either by closed-form compounding or by verifying the
defining property (NPV at the returned rate is zero).
"""
import datetime as dt

import pytest

from utils.irr import xirr, _net_present_value


class TestXirrKnownValues:
    """Cases with an answer derivable without the solver."""

    def test_single_period_doubling(self):
        """
        1000 in, 2000 out a year later. 2020 is a leap year, so the gap is
        366 days -- fractionally more than one 365.25-day year, making the
        annual rate fractionally under 100%.
        """
        years = (dt.date(2021, 1, 1) - dt.date(2020, 1, 1)).days / 365.25
        rate = xirr([
            (dt.date(2020, 1, 1), -1000.0),
            (dt.date(2021, 1, 1), 2000.0),
        ])
        assert rate == pytest.approx(2.0 ** (1 / years) - 1, abs=1e-4)

    def test_single_period_flat(self):
        """Money returned unchanged earns nothing."""
        rate = xirr([
            (dt.date(2020, 1, 1), -1000.0),
            (dt.date(2021, 1, 1), 1000.0),
        ])
        assert rate == pytest.approx(0.0, abs=1e-4)

    def test_multi_year_lump_sum_matches_cagr(self):
        """
        For a lump sum with no other flows, IRR is the CAGR by definition.
        1000 -> 1500 over 5 years is 1.5**(1/5) - 1 = 8.447%.
        """
        rate = xirr([
            (dt.date(2015, 1, 1), -1000.0),
            (dt.date(2020, 1, 1), 1500.0),
        ])
        expected = 1.5 ** (1 / ((dt.date(2020, 1, 1) - dt.date(2015, 1, 1)).days / 365.25)) - 1
        assert rate == pytest.approx(expected, abs=1e-4)

    def test_loss_gives_negative_rate(self):
        years = (dt.date(2021, 1, 1) - dt.date(2020, 1, 1)).days / 365.25
        rate = xirr([
            (dt.date(2020, 1, 1), -1000.0),
            (dt.date(2021, 1, 1), 500.0),
        ])
        assert rate == pytest.approx(0.5 ** (1 / years) - 1, abs=1e-4)


class TestXirrContributions:
    """The case that motivated this module: money paid in over time."""

    def test_regular_contributions_npv_is_zero(self):
        """
        The defining property: discounting every cashflow at the returned
        rate must net to zero. This validates the answer without assuming
        how it was found.
        """
        flows = [(dt.date(2020, 1, 1), -1000.0)]
        for month in range(1, 36):
            year = 2020 + (month // 12)
            m = (month % 12) + 1
            flows.append((dt.date(year, m, 1), -100.0))
        flows.append((dt.date(2023, 1, 1), 6000.0))

        rate = xirr(flows)
        assert rate is not None
        assert _net_present_value(
            rate,
            [(d - flows[0][0]).days / 365.25 for d, _ in sorted(flows)],
            [a for _, a in sorted(flows)],
        ) == pytest.approx(0.0, abs=1e-3)

    def test_contributions_beat_naive_ratio(self):
        """
        Money paid in late has less time to compound, so the money-weighted
        return must exceed the naive "profit over total paid in" figure.
        This is precisely the error the engine used to make.
        """
        flows = [(dt.date(2020, 1, 1), -1000.0)]
        for month in range(1, 12):
            flows.append((dt.date(2020, month + 1, 1), -1000.0))
        flows.append((dt.date(2021, 1, 1), 13200.0))

        rate = xirr(flows)
        naive = (13200.0 - 12000.0) / 12000.0  # 10%
        assert rate is not None
        assert rate > naive


class TestXirrEdgeCases:
    """Degenerate input must return None, never a fabricated number."""

    def test_empty(self):
        assert xirr([]) is None

    def test_single_flow(self):
        assert xirr([(dt.date(2020, 1, 1), -1000.0)]) is None

    def test_all_outflows(self):
        """No money ever comes back, so no rate exists."""
        assert xirr([
            (dt.date(2020, 1, 1), -1000.0),
            (dt.date(2021, 1, 1), -1000.0),
        ]) is None

    def test_all_inflows(self):
        assert xirr([
            (dt.date(2020, 1, 1), 1000.0),
            (dt.date(2021, 1, 1), 1000.0),
        ]) is None

    def test_total_loss_does_not_explode(self):
        """
        A near-total loss pushes the rate towards -100%, where the discount
        factor is undefined. It must stay bounded rather than diverge.
        """
        rate = xirr([
            (dt.date(2020, 1, 1), -1000.0),
            (dt.date(2021, 1, 1), 0.01),
        ])
        assert rate is None or -1.0 < rate < 0.0

    def test_unordered_input(self):
        """Cashflows given out of order must still solve correctly."""
        years = (dt.date(2021, 1, 1) - dt.date(2020, 1, 1)).days / 365.25
        rate = xirr([
            (dt.date(2021, 1, 1), 2000.0),
            (dt.date(2020, 1, 1), -1000.0),
        ])
        assert rate == pytest.approx(2.0 ** (1 / years) - 1, abs=1e-4)

    def test_bad_guess_still_converges(self):
        """
        A hostile starting guess must not break the result -- this is what
        the bisection fallback exists for.
        """
        flows = [
            (dt.date(2020, 1, 1), -1000.0),
            (dt.date(2021, 1, 1), 2000.0),
        ]
        years = (dt.date(2021, 1, 1) - dt.date(2020, 1, 1)).days / 365.25
        assert xirr(flows, guess=500.0) == pytest.approx(
            2.0 ** (1 / years) - 1, abs=1e-3
        )
