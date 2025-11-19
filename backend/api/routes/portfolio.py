"""
Portfolio calculation routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict

from database import get_db
from models.portfolio import (
    PortfolioCalculationRequest,
    PortfolioCalculationResponse,
    PortfolioComparisonRequest,
    PortfolioComparisonResponse,
    PortfolioCalculationError,
    InsufficientDataError,
    InvalidDateRangeError,
    PPRNotFoundError,
)
from services.portfolio_calculator import PortfolioCalculator

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.post("/calculate", response_model=PortfolioCalculationResponse)
def calculate_portfolio(
    request: PortfolioCalculationRequest,
    db: Session = Depends(get_db),
):
    """
    Calculate portfolio performance with financial metrics

    This endpoint calculates the historical performance of a portfolio consisting of
    PPR funds and optionally Bitcoin, with configurable allocations and rebalancing.

    **Features:**
    - Historical backtesting over specified date range
    - Multiple rebalancing frequencies (none, monthly, quarterly, yearly)
    - Comprehensive financial metrics (returns, volatility, Sharpe ratio, drawdown)
    - Detailed historical data points for charting

    **Example Request:**
    ```json
    {
        "ppr_allocations": [
            {
                "ppr_id": "uuid-here",
                "allocation_percentage": 70
            }
        ],
        "bitcoin_percentage": 30,
        "initial_investment": 10000,
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "rebalancing_frequency": "quarterly"
    }
    ```

    **Returns:**
    - Performance metrics (returns, volatility, Sharpe/Sortino ratios, drawdown)
    - Historical portfolio values for each date
    - Allocation breakdown with contribution to returns

    **Error Codes:**
    - 400: Invalid request (allocations don't sum to 100%, invalid dates, etc.)
    - 404: PPR not found
    - 422: Insufficient historical data for calculation
    """
    try:
        calculator = PortfolioCalculator(db)
        result = calculator.calculate_portfolio(request)
        return result

    except PPRNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidDateRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except PortfolioCalculationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio calculation error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.post("/compare", response_model=PortfolioComparisonResponse)
def compare_portfolios(
    request: PortfolioComparisonRequest,
    db: Session = Depends(get_db),
):
    """
    Compare multiple portfolio strategies side-by-side

    This endpoint allows comparing 2-5 different portfolio configurations to evaluate
    which strategy performs best based on your criteria.

    **Use Cases:**
    - Compare 100% PPR vs. PPR+Bitcoin hybrid strategies
    - Test different Bitcoin allocation percentages (0%, 10%, 20%, 30%)
    - Compare different rebalancing frequencies
    - Evaluate different PPR fund selections

    **Example Request:**
    ```json
    {
        "portfolios": [
            {
                "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 100}],
                "bitcoin_percentage": 0,
                "initial_investment": 10000,
                "start_date": "2020-01-01",
                "rebalancing_frequency": "quarterly"
            },
            {
                "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 70}],
                "bitcoin_percentage": 30,
                "initial_investment": 10000,
                "start_date": "2020-01-01",
                "rebalancing_frequency": "quarterly"
            }
        ],
        "portfolio_names": ["100% PPR", "70% PPR + 30% BTC"]
    }
    ```

    **Returns:**
    - Full calculation results for each portfolio
    - Comparison summary highlighting key differences
    - Side-by-side metrics for easy analysis

    **Limits:**
    - Minimum: 2 portfolios
    - Maximum: 5 portfolios
    """
    try:
        calculator = PortfolioCalculator(db)
        results = []

        # Calculate each portfolio
        for portfolio_request in request.portfolios:
            result = calculator.calculate_portfolio(portfolio_request)
            results.append(result)

        # Build comparison summary
        comparison_summary = _build_comparison_summary(results, request.portfolio_names)

        return PortfolioComparisonResponse(
            portfolios=results,
            comparison_summary=comparison_summary,
        )

    except PPRNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidDateRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except PortfolioCalculationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio calculation error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get("/metrics", response_model=Dict[str, str])
def get_available_metrics():
    """
    Get documentation for available portfolio metrics

    Returns a dictionary explaining each metric calculated by the portfolio engine.

    **Metrics Included:**
    - Total Return: Absolute and percentage returns
    - Annualized Return: Average yearly return
    - CAGR: Compound Annual Growth Rate
    - Volatility: Annualized standard deviation of returns
    - Sharpe Ratio: Risk-adjusted return (return per unit of risk)
    - Sortino Ratio: Downside risk-adjusted return
    - Max Drawdown: Largest peak-to-trough decline
    - Best/Worst Month: Extreme monthly performance
    """
    return {
        "total_return": "Absolute gain/loss in EUR from initial investment",
        "total_return_percentage": "Total return expressed as percentage of initial investment",
        "annualized_return": "Average yearly return percentage (same as CAGR)",
        "cagr": "Compound Annual Growth Rate - geometric average return per year",
        "volatility": "Annualized standard deviation of returns - measures risk/fluctuation",
        "sharpe_ratio": "Risk-adjusted return = (Return - Risk-free rate) / Volatility. Higher is better.",
        "sortino_ratio": "Downside risk-adjusted return - only penalizes downside volatility. Higher is better.",
        "max_drawdown": "Largest peak-to-trough decline in percentage terms. Negative number, closer to 0 is better.",
        "max_drawdown_duration_days": "Longest period (in days) the portfolio was underwater (below previous peak)",
        "final_value": "Portfolio value at the end of the period in EUR",
        "best_month": "Best monthly return percentage during the period",
        "worst_month": "Worst monthly return percentage during the period",
        "positive_months": "Number of months with positive returns",
        "total_months": "Total number of months in the analysis period",
        "rebalancing": "none = buy and hold, monthly = rebalance every ~30 days, quarterly = every ~90 days, yearly = every ~365 days",
    }


def _build_comparison_summary(
    results: list, portfolio_names: list = None
) -> Dict:
    """
    Build comparison summary for multiple portfolios

    Args:
        results: List of portfolio calculation results
        portfolio_names: Optional names for portfolios

    Returns:
        Dictionary with comparison summary
    """
    if not portfolio_names:
        portfolio_names = [f"Portfolio {i+1}" for i in range(len(results))]

    summary = {
        "portfolios": portfolio_names,
        "metrics_comparison": {},
    }

    # Compare key metrics
    metrics_to_compare = [
        "total_return_percentage",
        "cagr",
        "volatility",
        "sharpe_ratio",
        "max_drawdown",
        "final_value",
    ]

    for metric in metrics_to_compare:
        values = [float(getattr(result.metrics, metric)) for result in results]
        summary["metrics_comparison"][metric] = {
            "values": values,
            "best_index": values.index(max(values)) if metric != "max_drawdown" and metric != "volatility" else values.index(min(values)),
            "best_portfolio": portfolio_names[
                values.index(max(values)) if metric != "max_drawdown" and metric != "volatility" else values.index(min(values))
            ],
        }

    # Overall winner (based on Sharpe ratio)
    sharpe_values = [float(result.metrics.sharpe_ratio) for result in results]
    best_sharpe_idx = sharpe_values.index(max(sharpe_values))
    summary["recommended_portfolio"] = {
        "index": best_sharpe_idx,
        "name": portfolio_names[best_sharpe_idx],
        "reason": "Highest risk-adjusted return (Sharpe ratio)",
    }

    return summary
