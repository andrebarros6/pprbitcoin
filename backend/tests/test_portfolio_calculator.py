"""
Unit tests for portfolio calculator
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, MagicMock
import pandas as pd
import numpy as np

from services.portfolio_calculator import PortfolioCalculator
from models.portfolio import (
    PortfolioCalculationRequest,
    PortfolioAllocation,
    InsufficientDataError,
    InvalidDateRangeError,
    PPRNotFoundError,
)


class TestPortfolioCalculator:
    """Test cases for PortfolioCalculator"""

    def test_invalid_date_range(self):
        """Test that invalid date range raises error"""
        db_mock = Mock()
        calculator = PortfolioCalculator(db_mock)

        request = PortfolioCalculationRequest(
            ppr_allocations=[
                PortfolioAllocation(
                    ppr_id="550e8400-e29b-41d4-a716-446655440000",
                    allocation_percentage=Decimal("100"),
                )
            ],
            bitcoin_percentage=Decimal("0"),
            initial_investment=Decimal("10000"),
            start_date=date(2024, 1, 1),
            end_date=date(2020, 1, 1),  # End before start
            rebalancing_frequency="none",
        )

        with pytest.raises(InvalidDateRangeError):
            calculator.calculate_portfolio(request)

    def test_ppr_not_found(self):
        """Test that non-existent PPR raises error"""
        db_mock = Mock()
        db_mock.query.return_value.filter.return_value.first.return_value = None

        calculator = PortfolioCalculator(db_mock)

        request = PortfolioCalculationRequest(
            ppr_allocations=[
                PortfolioAllocation(
                    ppr_id="550e8400-e29b-41d4-a716-446655440000",
                    allocation_percentage=Decimal("100"),
                )
            ],
            bitcoin_percentage=Decimal("0"),
            initial_investment=Decimal("10000"),
            start_date=date(2020, 1, 1),
            end_date=date(2024, 1, 1),
            rebalancing_frequency="none",
        )

        with pytest.raises(PPRNotFoundError):
            calculator.calculate_portfolio(request)

    def test_allocation_validation(self):
        """Test that allocations are validated correctly"""
        # Valid: 70% PPR + 30% Bitcoin = 100%
        valid_request = PortfolioCalculationRequest(
            ppr_allocations=[
                PortfolioAllocation(
                    ppr_id="550e8400-e29b-41d4-a716-446655440000",
                    allocation_percentage=Decimal("70"),
                )
            ],
            bitcoin_percentage=Decimal("30"),
            initial_investment=Decimal("10000"),
            start_date=date(2020, 1, 1),
            rebalancing_frequency="none",
        )
        assert valid_request.bitcoin_percentage == Decimal("30")

        # Invalid: 80% PPR + 30% Bitcoin = 110%
        with pytest.raises(ValueError):
            PortfolioCalculationRequest(
                ppr_allocations=[
                    PortfolioAllocation(
                        ppr_id="550e8400-e29b-41d4-a716-446655440000",
                        allocation_percentage=Decimal("80"),
                    )
                ],
                bitcoin_percentage=Decimal("30"),
                initial_investment=Decimal("10000"),
                start_date=date(2020, 1, 1),
                rebalancing_frequency="none",
            )

    def test_multiple_ppr_allocation(self):
        """Test portfolio with multiple PPR funds"""
        # Valid: 40% PPR1 + 30% PPR2 + 30% Bitcoin = 100%
        valid_request = PortfolioCalculationRequest(
            ppr_allocations=[
                PortfolioAllocation(
                    ppr_id="550e8400-e29b-41d4-a716-446655440000",
                    allocation_percentage=Decimal("40"),
                ),
                PortfolioAllocation(
                    ppr_id="550e8400-e29b-41d4-a716-446655440001",
                    allocation_percentage=Decimal("30"),
                ),
            ],
            bitcoin_percentage=Decimal("30"),
            initial_investment=Decimal("10000"),
            start_date=date(2020, 1, 1),
            rebalancing_frequency="quarterly",
        )
        assert len(valid_request.ppr_allocations) == 2

    def test_should_rebalance_monthly(self):
        """Test monthly rebalancing logic"""
        db_mock = Mock()
        calculator = PortfolioCalculator(db_mock)

        from datetime import datetime

        start = datetime(2024, 1, 1)
        after_30_days = datetime(2024, 1, 31)
        after_60_days = datetime(2024, 3, 1)

        # Should not rebalance with "none"
        assert not calculator._should_rebalance(after_30_days, start, "none")

        # Should rebalance after 30 days with monthly
        assert calculator._should_rebalance(after_30_days, start, "monthly")

        # Should not rebalance before 30 days
        after_20_days = datetime(2024, 1, 21)
        assert not calculator._should_rebalance(after_20_days, start, "monthly")

    def test_should_rebalance_quarterly(self):
        """Test quarterly rebalancing logic"""
        db_mock = Mock()
        calculator = PortfolioCalculator(db_mock)

        from datetime import datetime

        start = datetime(2024, 1, 1)
        after_90_days = datetime(2024, 4, 1)

        # Should rebalance after 90 days with quarterly
        assert calculator._should_rebalance(after_90_days, start, "quarterly")

        # Should not rebalance before 90 days
        after_60_days = datetime(2024, 3, 1)
        assert not calculator._should_rebalance(after_60_days, start, "quarterly")

    def test_should_rebalance_yearly(self):
        """Test yearly rebalancing logic"""
        db_mock = Mock()
        calculator = PortfolioCalculator(db_mock)

        from datetime import datetime

        start = datetime(2024, 1, 1)
        after_365_days = datetime(2025, 1, 1)

        # Should rebalance after 365 days with yearly
        assert calculator._should_rebalance(after_365_days, start, "yearly")

        # Should not rebalance before 365 days
        after_180_days = datetime(2024, 7, 1)
        assert not calculator._should_rebalance(after_180_days, start, "yearly")


class TestPerformanceMetrics:
    """Test performance metric calculations"""

    def test_cagr_calculation(self):
        """Test CAGR calculation logic"""
        # CAGR = ((Final Value / Initial Value)^(1/Years)) - 1
        # Example: 10000 -> 15000 in 3 years
        # CAGR = ((15000/10000)^(1/3)) - 1 = 0.1447 = 14.47%

        initial = 10000
        final = 15000
        years = 3
        expected_cagr = (((final / initial) ** (1 / years)) - 1) * 100

        assert abs(expected_cagr - 14.47) < 0.1  # Allow small difference

    def test_volatility_calculation(self):
        """Test volatility (standard deviation) calculation"""
        # Create sample returns
        returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02])  # Daily returns
        volatility = returns.std() * np.sqrt(252) * 100  # Annualized

        assert volatility > 0
        assert isinstance(volatility, (float, np.floating))

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""
        # Sharpe = (Return - Risk-free rate) / Volatility
        # With 0% risk-free rate: Sharpe = Return / Volatility

        annual_return = 15.0  # 15% annual return
        volatility = 10.0  # 10% volatility
        expected_sharpe = annual_return / volatility  # = 1.5

        assert abs(expected_sharpe - 1.5) < 0.01

    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation"""
        # Portfolio values: [100, 120, 110, 105, 115, 130]
        # Returns: [0.20, -0.0833, -0.0455, 0.0952, 0.1304]
        # Cumulative: [1.0, 1.20, 1.10, 1.05, 1.15, 1.30]
        # Running max: [1.0, 1.20, 1.20, 1.20, 1.20, 1.30]
        # Drawdown: [0, 0, -8.33%, -12.5%, -4.17%, 0]
        # Max drawdown: -12.5%

        values = pd.Series([100, 120, 110, 105, 115, 130])
        returns = values.pct_change().dropna()
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        assert max_drawdown < 0
        assert abs(max_drawdown - (-12.5)) < 0.5  # Approximately -12.5%


# Integration test helpers
def create_mock_ppr(ppr_id: str, nome: str = "Test PPR"):
    """Create a mock PPR object"""
    ppr = Mock()
    ppr.id = ppr_id
    ppr.nome = nome
    ppr.gestor = "Test Gestor"
    ppr.categoria = "Moderado"
    return ppr


def create_mock_ppr_historical_data(ppr_id: str, start_date: date, end_date: date):
    """Create mock PPR historical data"""
    data = []
    current = start_date
    value = 100.0

    while current <= end_date:
        item = Mock()
        item.data = current
        item.valor_quota = value
        item.ppr_id = ppr_id
        data.append(item)

        # Simulate growth with some volatility
        value *= 1 + np.random.normal(0.0005, 0.01)  # ~0.05% daily growth with volatility
        current = date.fromordinal(current.toordinal() + 1)

    return data


def create_mock_bitcoin_historical_data(start_date: date, end_date: date):
    """Create mock Bitcoin historical data"""
    data = []
    current = start_date
    price = 20000.0

    while current <= end_date:
        item = Mock()
        item.data = current
        item.preco_eur = price
        data.append(item)

        # Simulate Bitcoin volatility
        price *= 1 + np.random.normal(0.001, 0.03)  # Higher volatility than PPR
        current = date.fromordinal(current.toordinal() + 1)

    return data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
