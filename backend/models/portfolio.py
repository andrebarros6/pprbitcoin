"""
Portfolio models and schemas for portfolio calculations
"""
from pydantic import BaseModel, Field, field_validator, UUID4
from typing import List, Optional, Literal
from datetime import date
from decimal import Decimal


# Request Schemas

class PortfolioAllocation(BaseModel):
    """
    Individual PPR allocation in a portfolio
    """
    ppr_id: UUID4 = Field(..., description="UUID of the PPR fund")
    allocation_percentage: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage allocation (0-100)"
    )


class PortfolioCalculationRequest(BaseModel):
    """
    Request schema for portfolio calculation
    """
    ppr_allocations: List[PortfolioAllocation] = Field(
        ...,
        min_length=1,
        description="List of PPR allocations"
    )
    bitcoin_percentage: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        description="Bitcoin allocation percentage (0-100)"
    )
    initial_investment: Decimal = Field(
        default=Decimal("10000"),
        gt=0,
        description="Initial investment amount in EUR"
    )
    start_date: date = Field(
        ...,
        description="Start date for backtesting (YYYY-MM-DD)"
    )
    end_date: Optional[date] = Field(
        default=None,
        description="End date for backtesting (defaults to latest available)"
    )
    rebalancing_frequency: Literal["none", "monthly", "quarterly", "yearly"] = Field(
        default="quarterly",
        description="Portfolio rebalancing frequency"
    )

    @field_validator("ppr_allocations")
    @classmethod
    def validate_ppr_allocations(cls, v: List[PortfolioAllocation]) -> List[PortfolioAllocation]:
        """Validate that PPR allocations sum correctly with Bitcoin allocation"""
        total_ppr = sum(allocation.allocation_percentage for allocation in v)
        if total_ppr < 0 or total_ppr > 100:
            raise ValueError(f"Total PPR allocation must be between 0-100%, got {total_ppr}%")
        return v

    @field_validator("bitcoin_percentage")
    @classmethod
    def validate_total_allocation(cls, v: Decimal, info) -> Decimal:
        """Validate that total allocation (PPR + Bitcoin) equals 100%"""
        if "ppr_allocations" in info.data:
            total_ppr = sum(
                allocation.allocation_percentage
                for allocation in info.data["ppr_allocations"]
            )
            total = total_ppr + v
            if abs(total - Decimal("100")) > Decimal("0.01"):  # Allow small floating point differences
                raise ValueError(
                    f"Total allocation must equal 100%, got {total}% "
                    f"(PPR: {total_ppr}%, Bitcoin: {v}%)"
                )
        return v


class PortfolioComparisonRequest(BaseModel):
    """
    Request schema for comparing multiple portfolio strategies
    """
    portfolios: List[PortfolioCalculationRequest] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of portfolios to compare (2-5 portfolios)"
    )
    portfolio_names: Optional[List[str]] = Field(
        default=None,
        description="Optional names for each portfolio"
    )


# Response Schemas

class PerformanceMetrics(BaseModel):
    """
    Portfolio performance metrics
    """
    total_return: Decimal = Field(..., description="Total return in EUR")
    total_return_percentage: Decimal = Field(..., description="Total return as percentage")
    annualized_return: Decimal = Field(..., description="Annualized return percentage")
    cagr: Decimal = Field(..., description="Compound Annual Growth Rate")
    volatility: Decimal = Field(..., description="Annualized volatility (standard deviation)")
    sharpe_ratio: Decimal = Field(..., description="Sharpe ratio (assuming 0% risk-free rate)")
    sortino_ratio: Decimal = Field(..., description="Sortino ratio (downside deviation)")
    max_drawdown: Decimal = Field(..., description="Maximum drawdown percentage")
    max_drawdown_duration_days: int = Field(..., description="Maximum drawdown duration in days")
    final_value: Decimal = Field(..., description="Final portfolio value in EUR")
    best_month: Decimal = Field(..., description="Best monthly return percentage")
    worst_month: Decimal = Field(..., description="Worst monthly return percentage")
    positive_months: int = Field(..., description="Number of positive months")
    total_months: int = Field(..., description="Total number of months")


class HistoricalDataPoint(BaseModel):
    """
    Single point in portfolio historical performance
    """
    data: date = Field(..., description="Date of the data point")
    portfolio_value: Decimal = Field(..., description="Total portfolio value in EUR")
    ppr_value: Decimal = Field(..., description="PPR component value in EUR")
    bitcoin_value: Decimal = Field(..., description="Bitcoin component value in EUR")
    total_return: Decimal = Field(..., description="Cumulative return percentage")
    drawdown: Decimal = Field(..., description="Current drawdown from peak")


class AllocationBreakdown(BaseModel):
    """
    Detailed allocation breakdown
    """
    ppr_id: UUID4
    ppr_name: str
    allocation_percentage: Decimal
    current_value: Decimal
    contribution_to_return: Decimal


class PortfolioCalculationResponse(BaseModel):
    """
    Response schema for portfolio calculation
    """
    portfolio_config: PortfolioCalculationRequest = Field(
        ...,
        description="Original portfolio configuration"
    )
    metrics: PerformanceMetrics = Field(
        ...,
        description="Performance metrics"
    )
    historical_data: List[HistoricalDataPoint] = Field(
        ...,
        description="Historical portfolio performance data"
    )
    allocation_breakdown: List[AllocationBreakdown] = Field(
        ...,
        description="Detailed breakdown by asset"
    )
    calculation_date: date = Field(
        ...,
        description="Date when calculation was performed"
    )


class PortfolioComparisonResponse(BaseModel):
    """
    Response schema for portfolio comparison
    """
    portfolios: List[PortfolioCalculationResponse] = Field(
        ...,
        description="Results for each portfolio"
    )
    comparison_summary: dict = Field(
        ...,
        description="Summary comparing key metrics across portfolios"
    )


# Custom Exceptions

class PortfolioCalculationError(Exception):
    """Base exception for portfolio calculation errors"""
    pass


class InsufficientDataError(PortfolioCalculationError):
    """Raised when there is insufficient historical data for calculation"""
    pass


class InvalidDateRangeError(PortfolioCalculationError):
    """Raised when date range is invalid"""
    pass


class PPRNotFoundError(PortfolioCalculationError):
    """Raised when a PPR ID is not found in database"""
    pass
