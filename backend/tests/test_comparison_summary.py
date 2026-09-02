"""
Tests for which portfolio a comparison names as "best" per metric.

The bug these guard against: losses are reported as negative numbers, so
picking the minimum named the *deepest* drawdown the winner -- the live API
reported -24.84% as better than -18.91%. That is backwards on exactly the
metric a cautious saver is scanning for.
"""
from decimal import Decimal
from types import SimpleNamespace

from api.routes.portfolio import _build_comparison_summary


def _result(**metrics):
    """A stand-in for a calculation result carrying only the metrics."""
    defaults = dict(
        total_return_percentage=Decimal("10"),
        cagr=Decimal("5"),
        volatility=Decimal("10"),
        sharpe_ratio=Decimal("1"),
        max_drawdown=Decimal("-10"),
        final_value=Decimal("11000"),
    )
    defaults.update(metrics)
    return SimpleNamespace(metrics=SimpleNamespace(**defaults))


def _summary(results, names):
    return _build_comparison_summary(results, names)["metrics_comparison"]


class TestDrawdownIsNotInverted:
    """A shallower loss must win, not a deeper one."""

    def test_shallower_drawdown_wins(self):
        mc = _summary(
            [
                _result(max_drawdown=Decimal("-18.91")),
                _result(max_drawdown=Decimal("-24.84")),
            ],
            ["conservative", "risky"],
        )
        assert mc["max_drawdown"]["best_portfolio"] == "conservative"
        assert mc["max_drawdown"]["best_index"] == 0

    def test_shallower_drawdown_wins_when_listed_second(self):
        """Order must not decide the winner."""
        mc = _summary(
            [
                _result(max_drawdown=Decimal("-40.00")),
                _result(max_drawdown=Decimal("-5.00")),
            ],
            ["risky", "conservative"],
        )
        assert mc["max_drawdown"]["best_portfolio"] == "conservative"

    def test_zero_drawdown_wins(self):
        """A portfolio that never fell is the best possible case."""
        mc = _summary(
            [
                _result(max_drawdown=Decimal("-12.00")),
                _result(max_drawdown=Decimal("0")),
            ],
            ["fell", "never fell"],
        )
        assert mc["max_drawdown"]["best_portfolio"] == "never fell"


class TestOtherMetricsUnchanged:
    """The fix must not disturb the metrics that were already correct."""

    def test_lower_volatility_wins(self):
        mc = _summary(
            [_result(volatility=Decimal("6.8")), _result(volatility=Decimal("9.66"))],
            ["calm", "wild"],
        )
        assert mc["volatility"]["best_portfolio"] == "calm"

    def test_higher_return_wins(self):
        mc = _summary(
            [
                _result(total_return_percentage=Decimal("16.21")),
                _result(total_return_percentage=Decimal("76.01")),
            ],
            ["low", "high"],
        )
        assert mc["total_return_percentage"]["best_portfolio"] == "high"

    def test_higher_final_value_wins(self):
        mc = _summary(
            [_result(final_value=Decimal("25193")), _result(final_value=Decimal("34008"))],
            ["small", "large"],
        )
        assert mc["final_value"]["best_portfolio"] == "large"

    def test_higher_sharpe_wins(self):
        mc = _summary(
            [_result(sharpe_ratio=Decimal("0.5")), _result(sharpe_ratio=Decimal("1.8"))],
            ["poor", "good"],
        )
        assert mc["sharpe_ratio"]["best_portfolio"] == "good"

    def test_values_are_reported_in_input_order(self):
        """The values list must stay aligned with the portfolios given."""
        mc = _summary(
            [
                _result(max_drawdown=Decimal("-18.91")),
                _result(max_drawdown=Decimal("-24.84")),
            ],
            ["a", "b"],
        )
        assert mc["max_drawdown"]["values"] == [-18.91, -24.84]
