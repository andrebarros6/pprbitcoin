"""
Portfolio calculation service with financial metrics and backtesting
"""
import pandas as pd
import numpy as np
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.ppr import PPR, PPRHistoricalData
from models.bitcoin import BitcoinHistoricalData
from models.portfolio import (
    PortfolioCalculationRequest,
    PortfolioCalculationResponse,
    PerformanceMetrics,
    HistoricalDataPoint,
    AllocationBreakdown,
    InsufficientDataError,
    InvalidDateRangeError,
    PPRNotFoundError,
)


class PortfolioCalculator:
    """
    Service for calculating portfolio performance and metrics
    """

    def __init__(self, db: Session):
        """
        Initialize portfolio calculator

        Args:
            db: Database session
        """
        self.db = db
        self.risk_free_rate = Decimal("0")  # Can be configurable

    def calculate_portfolio(
        self, request: PortfolioCalculationRequest
    ) -> PortfolioCalculationResponse:
        """
        Main method to calculate portfolio performance

        Args:
            request: Portfolio calculation request

        Returns:
            Portfolio calculation response with all metrics

        Raises:
            PPRNotFoundError: If any PPR ID is not found
            InsufficientDataError: If insufficient historical data
            InvalidDateRangeError: If date range is invalid
        """
        # Validate date range
        end_date = request.end_date or date.today()
        if request.start_date >= end_date:
            raise InvalidDateRangeError(
                f"Start date {request.start_date} must be before end date {end_date}"
            )

        # Fetch and validate PPRs
        pprs = self._fetch_and_validate_pprs(request.ppr_allocations)

        # Fetch historical data
        ppr_data = self._fetch_ppr_historical_data(
            request.ppr_allocations, request.start_date, end_date
        )
        bitcoin_data = self._fetch_bitcoin_historical_data(request.start_date, end_date)

        # Merge and align data
        aligned_data = self._align_historical_data(ppr_data, bitcoin_data)

        if aligned_data.empty:
            raise InsufficientDataError(
                f"No overlapping data found for date range {request.start_date} to {end_date}"
            )

        # Calculate portfolio values over time
        portfolio_values = self._calculate_portfolio_values(
            aligned_data, request, pprs
        )

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(
            portfolio_values, request.initial_investment
        )

        # Build historical data points
        historical_data = self._build_historical_data_points(portfolio_values)

        # Build allocation breakdown
        allocation_breakdown = self._build_allocation_breakdown(
            request, pprs, portfolio_values
        )

        return PortfolioCalculationResponse(
            portfolio_config=request,
            metrics=metrics,
            historical_data=historical_data,
            allocation_breakdown=allocation_breakdown,
            calculation_date=date.today(),
        )

    def _fetch_and_validate_pprs(
        self, ppr_allocations: List
    ) -> Dict[str, PPR]:
        """
        Fetch PPRs from database and validate they exist

        Args:
            ppr_allocations: List of PPR allocations

        Returns:
            Dictionary mapping PPR ID to PPR object

        Raises:
            PPRNotFoundError: If any PPR is not found
        """
        pprs = {}
        for allocation in ppr_allocations:
            ppr = self.db.query(PPR).filter(PPR.id == allocation.ppr_id).first()
            if not ppr:
                raise PPRNotFoundError(f"PPR with ID {allocation.ppr_id} not found")
            pprs[str(allocation.ppr_id)] = ppr
        return pprs

    def _fetch_ppr_historical_data(
        self, ppr_allocations: List, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Fetch PPR historical data and combine into a single DataFrame

        Args:
            ppr_allocations: List of PPR allocations
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with PPR prices indexed by date
        """
        ppr_dataframes = []

        for allocation in ppr_allocations:
            # Query historical data
            historical_data = (
                self.db.query(PPRHistoricalData)
                .filter(
                    and_(
                        PPRHistoricalData.ppr_id == allocation.ppr_id,
                        PPRHistoricalData.data >= start_date,
                        PPRHistoricalData.data <= end_date,
                    )
                )
                .order_by(PPRHistoricalData.data.asc())
                .all()
            )

            if not historical_data:
                raise InsufficientDataError(
                    f"No historical data found for PPR {allocation.ppr_id} "
                    f"in date range {start_date} to {end_date}"
                )

            # Convert to DataFrame
            df = pd.DataFrame(
                [
                    {
                        "data": item.data,
                        f"ppr_{allocation.ppr_id}": float(item.valor_quota),
                    }
                    for item in historical_data
                ]
            )
            df["data"] = pd.to_datetime(df["data"])
            df.set_index("data", inplace=True)
            ppr_dataframes.append(df)

        # Merge all PPR dataframes
        if ppr_dataframes:
            combined_df = pd.concat(ppr_dataframes, axis=1)
            return combined_df
        else:
            return pd.DataFrame()

    def _fetch_bitcoin_historical_data(
        self, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Fetch Bitcoin historical data

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with Bitcoin prices indexed by date
        """
        historical_data = (
            self.db.query(BitcoinHistoricalData)
            .filter(
                and_(
                    BitcoinHistoricalData.data >= start_date,
                    BitcoinHistoricalData.data <= end_date,
                )
            )
            .order_by(BitcoinHistoricalData.data.asc())
            .all()
        )

        if not historical_data:
            # If no Bitcoin allocation, this is okay
            return pd.DataFrame()

        df = pd.DataFrame(
            [
                {"data": item.data, "bitcoin_price": float(item.preco_eur)}
                for item in historical_data
            ]
        )
        df["data"] = pd.to_datetime(df["data"])
        df.set_index("data", inplace=True)
        return df

    def _align_historical_data(
        self, ppr_data: pd.DataFrame, bitcoin_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Align PPR and Bitcoin historical data to common dates

        Args:
            ppr_data: DataFrame with PPR prices
            bitcoin_data: DataFrame with Bitcoin prices

        Returns:
            Aligned DataFrame with all data
        """
        if bitcoin_data.empty:
            # No Bitcoin data, just use PPR data
            return ppr_data

        # Merge dataframes
        combined = pd.concat([ppr_data, bitcoin_data], axis=1)

        # Forward fill missing values (use last known price)
        combined = combined.ffill()

        # Drop rows with any remaining NaN (beginning of series)
        combined = combined.dropna()

        return combined

    def _calculate_portfolio_values(
        self,
        aligned_data: pd.DataFrame,
        request: PortfolioCalculationRequest,
        pprs: Dict[str, PPR],
    ) -> pd.DataFrame:
        """
        Calculate portfolio values over time with rebalancing

        Args:
            aligned_data: Aligned historical data
            request: Portfolio calculation request
            pprs: Dictionary of PPR objects

        Returns:
            DataFrame with portfolio values over time
        """
        initial_investment = float(request.initial_investment)
        bitcoin_pct = float(request.bitcoin_percentage) / 100

        # Calculate initial allocation
        portfolio_values = []
        dates = aligned_data.index

        # Initial units purchased
        initial_units = {}
        initial_date = dates[0]

        # Calculate PPR units
        for allocation in request.ppr_allocations:
            ppr_id = str(allocation.ppr_id)
            allocation_pct = float(allocation.allocation_percentage) / 100
            allocation_amount = initial_investment * allocation_pct
            initial_price = float(aligned_data.loc[initial_date, f"ppr_{allocation.ppr_id}"])
            initial_units[f"ppr_{allocation.ppr_id}"] = allocation_amount / initial_price

        # Calculate Bitcoin units
        if bitcoin_pct > 0:
            bitcoin_allocation = initial_investment * bitcoin_pct
            initial_bitcoin_price = float(aligned_data.loc[initial_date, "bitcoin_price"])
            initial_units["bitcoin"] = bitcoin_allocation / initial_bitcoin_price
        else:
            initial_units["bitcoin"] = 0

        # Track current units (will change with rebalancing)
        current_units = initial_units.copy()
        last_rebalance_date = initial_date

        # Calculate portfolio value for each date
        for current_date in dates:
            # Check if rebalancing is needed
            if self._should_rebalance(
                current_date, last_rebalance_date, request.rebalancing_frequency
            ):
                current_units = self._rebalance_portfolio(
                    aligned_data,
                    current_date,
                    current_units,
                    request,
                )
                last_rebalance_date = current_date

            # Calculate current portfolio value
            ppr_value = 0
            for allocation in request.ppr_allocations:
                col_name = f"ppr_{allocation.ppr_id}"
                current_price = float(aligned_data.loc[current_date, col_name])
                ppr_value += current_units[col_name] * current_price

            bitcoin_value = 0
            if "bitcoin_price" in aligned_data.columns and bitcoin_pct > 0:
                bitcoin_price = float(aligned_data.loc[current_date, "bitcoin_price"])
                bitcoin_value = current_units["bitcoin"] * bitcoin_price

            total_value = ppr_value + bitcoin_value

            portfolio_values.append(
                {
                    "date": current_date.date(),
                    "ppr_value": ppr_value,
                    "bitcoin_value": bitcoin_value,
                    "total_value": total_value,
                }
            )

        return pd.DataFrame(portfolio_values)

    def _should_rebalance(
        self, current_date: datetime, last_rebalance: datetime, frequency: str
    ) -> bool:
        """
        Check if portfolio should be rebalanced

        Args:
            current_date: Current date
            last_rebalance: Last rebalancing date
            frequency: Rebalancing frequency

        Returns:
            True if should rebalance
        """
        if frequency == "none":
            return False

        time_diff = (current_date - last_rebalance).days

        if frequency == "monthly":
            return time_diff >= 30
        elif frequency == "quarterly":
            return time_diff >= 90
        elif frequency == "yearly":
            return time_diff >= 365

        return False

    def _rebalance_portfolio(
        self,
        aligned_data: pd.DataFrame,
        rebalance_date: datetime,
        current_units: Dict,
        request: PortfolioCalculationRequest,
    ) -> Dict:
        """
        Rebalance portfolio to target allocations

        Args:
            aligned_data: Aligned historical data
            rebalance_date: Date to rebalance
            current_units: Current units held
            request: Portfolio request with target allocations

        Returns:
            New units after rebalancing
        """
        # Calculate current total value
        total_value = 0
        for allocation in request.ppr_allocations:
            col_name = f"ppr_{allocation.ppr_id}"
            current_price = float(aligned_data.loc[rebalance_date, col_name])
            total_value += current_units[col_name] * current_price

        if "bitcoin_price" in aligned_data.columns:
            bitcoin_price = float(aligned_data.loc[rebalance_date, "bitcoin_price"])
            total_value += current_units["bitcoin"] * bitcoin_price

        # Calculate new units based on target allocations
        new_units = {}
        bitcoin_pct = float(request.bitcoin_percentage) / 100

        for allocation in request.ppr_allocations:
            col_name = f"ppr_{allocation.ppr_id}"
            allocation_pct = float(allocation.allocation_percentage) / 100
            target_value = total_value * allocation_pct
            current_price = float(aligned_data.loc[rebalance_date, col_name])
            new_units[col_name] = target_value / current_price

        # Rebalance Bitcoin
        if "bitcoin_price" in aligned_data.columns and bitcoin_pct > 0:
            target_bitcoin_value = total_value * bitcoin_pct
            bitcoin_price = float(aligned_data.loc[rebalance_date, "bitcoin_price"])
            new_units["bitcoin"] = target_bitcoin_value / bitcoin_price
        else:
            new_units["bitcoin"] = 0

        return new_units

    def _calculate_performance_metrics(
        self, portfolio_values: pd.DataFrame, initial_investment: Decimal
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics

        Args:
            portfolio_values: DataFrame with portfolio values over time
            initial_investment: Initial investment amount

        Returns:
            Performance metrics
        """
        initial_value = float(initial_investment)
        final_value = portfolio_values.iloc[-1]["total_value"]
        values = portfolio_values["total_value"].values

        # Total returns
        total_return = final_value - initial_value
        total_return_pct = (total_return / initial_value) * 100

        # Calculate returns series
        returns = pd.Series(values).pct_change().dropna()

        # Number of periods
        num_days = len(portfolio_values)
        num_years = num_days / 365.25

        # CAGR
        cagr = (((final_value / initial_value) ** (1 / num_years)) - 1) * 100 if num_years > 0 else 0

        # Annualized return
        annualized_return = cagr

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100  # Assuming daily data, 252 trading days

        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe_ratio = (annualized_return / volatility) if volatility > 0 else 0

        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) * 100
        sortino_ratio = (annualized_return / downside_deviation) if downside_deviation > 0 else 0

        # Maximum Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # Maximum Drawdown Duration
        # Find the longest period underwater
        is_underwater = drawdown < -0.01  # More than 0.01% drawdown
        if is_underwater.any():
            # Group consecutive underwater periods
            underwater_periods = (is_underwater != is_underwater.shift()).cumsum()
            max_dd_duration = (
                is_underwater.groupby(underwater_periods).sum().max()
                if is_underwater.any()
                else 0
            )
        else:
            max_dd_duration = 0

        # Monthly statistics (approximate from daily data)
        # Group by month
        portfolio_values["month"] = pd.to_datetime(portfolio_values["date"]).dt.to_period("M")
        monthly_returns = (
            portfolio_values.groupby("month")["total_value"]
            .last()
            .pct_change()
            .dropna()
            * 100
        )

        best_month = monthly_returns.max() if len(monthly_returns) > 0 else 0
        worst_month = monthly_returns.min() if len(monthly_returns) > 0 else 0
        positive_months = (monthly_returns > 0).sum() if len(monthly_returns) > 0 else 0
        total_months = len(monthly_returns)

        return PerformanceMetrics(
            total_return=Decimal(str(round(total_return, 2))),
            total_return_percentage=Decimal(str(round(total_return_pct, 2))),
            annualized_return=Decimal(str(round(annualized_return, 2))),
            cagr=Decimal(str(round(cagr, 2))),
            volatility=Decimal(str(round(volatility, 2))),
            sharpe_ratio=Decimal(str(round(sharpe_ratio, 2))),
            sortino_ratio=Decimal(str(round(sortino_ratio, 2))),
            max_drawdown=Decimal(str(round(max_drawdown, 2))),
            max_drawdown_duration_days=int(max_dd_duration),
            final_value=Decimal(str(round(final_value, 2))),
            best_month=Decimal(str(round(best_month, 2))),
            worst_month=Decimal(str(round(worst_month, 2))),
            positive_months=int(positive_months),
            total_months=int(total_months),
        )

    def _build_historical_data_points(
        self, portfolio_values: pd.DataFrame
    ) -> List[HistoricalDataPoint]:
        """
        Build historical data points for response

        Args:
            portfolio_values: DataFrame with portfolio values

        Returns:
            List of historical data points
        """
        initial_value = portfolio_values.iloc[0]["total_value"]
        peak_value = initial_value

        historical_data = []
        for _, row in portfolio_values.iterrows():
            total_value = row["total_value"]
            total_return = ((total_value - initial_value) / initial_value) * 100

            # Update peak
            if total_value > peak_value:
                peak_value = total_value

            # Calculate drawdown
            drawdown = ((total_value - peak_value) / peak_value) * 100 if peak_value > 0 else 0

            historical_data.append(
                HistoricalDataPoint(
                    data=row["date"],
                    portfolio_value=Decimal(str(round(total_value, 2))),
                    ppr_value=Decimal(str(round(row["ppr_value"], 2))),
                    bitcoin_value=Decimal(str(round(row["bitcoin_value"], 2))),
                    total_return=Decimal(str(round(total_return, 2))),
                    drawdown=Decimal(str(round(drawdown, 2))),
                )
            )

        return historical_data

    def _build_allocation_breakdown(
        self,
        request: PortfolioCalculationRequest,
        pprs: Dict[str, PPR],
        portfolio_values: pd.DataFrame,
    ) -> List[AllocationBreakdown]:
        """
        Build allocation breakdown for response

        Args:
            request: Portfolio calculation request
            pprs: Dictionary of PPR objects
            portfolio_values: DataFrame with portfolio values

        Returns:
            List of allocation breakdowns
        """
        initial_value = float(request.initial_investment)
        final_row = portfolio_values.iloc[-1]
        final_value = final_row["total_value"]

        breakdown = []

        # PPR breakdown
        for allocation in request.ppr_allocations:
            ppr_id = str(allocation.ppr_id)
            ppr = pprs[ppr_id]
            allocation_pct = allocation.allocation_percentage
            current_value = (final_row["ppr_value"] * float(allocation_pct)) / float(sum(
                a.allocation_percentage for a in request.ppr_allocations
            ))
            contribution = ((current_value - (initial_value * float(allocation_pct) / 100)) / initial_value) * 100

            breakdown.append(
                AllocationBreakdown(
                    ppr_id=allocation.ppr_id,
                    ppr_name=ppr.nome,
                    allocation_percentage=allocation_pct,
                    current_value=Decimal(str(round(current_value, 2))),
                    contribution_to_return=Decimal(str(round(contribution, 2))),
                )
            )

        return breakdown
